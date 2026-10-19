from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user, get_db_session, require_role
from app.auth.jwt_handler import create_access_token
from app.auth.password import hash_password, verify_password
from app.auth.rbac import Role
from app.config.settings import get_settings
from app.repositories.user_repository import UserRepository
from app.schemas.auth_schema import LoginRequest, TokenResponse, UserCreateRequest, UserResponse
from app.models.user import User
from app.utils.exceptions import AuthenticationError, ValidationAppError

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db_session),
):
    username = payload.username.strip() if payload.username else ""
    password = payload.password or ""

    if not username or not password:
        raise AuthenticationError("Invalid username or password.")

    users = UserRepository(db)
    user = users.get_by_username(username) or users.get_by_email(username)

    # Resolve client metadata for audit log (never raise on failure)
    ip  = request.client.host if request.client else None
    ua  = request.headers.get("user-agent", "")
    device = "mobile" if any(k in ua.lower() for k in ("mobile", "android", "iphone")) else "desktop"

    if user is None or not user.is_active or not verify_password(password, user.hashed_password):
        # Record failed login event
        try:
            _record_login(
                db=db,
                username=username or "",
                user_id=user.id if user else None,
                success=False,
                ip=ip,
                ua=ua,
                device=device,
                reason="invalid_credentials" if user else "user_not_found",
            )
        except Exception:
            pass
        raise AuthenticationError("Invalid username or password.")

    # Record successful login
    try:
        _record_login(db=db, username=user.username, user_id=user.id,
                      success=True, ip=ip, ua=ua, device=device)
    except Exception:
        pass

    settings = get_settings()
    token = create_access_token(subject=user.id, role=user.role, extra_claims={"username": user.username})
    return TokenResponse(access_token=token, expires_in_minutes=settings.jwt_access_token_expire_minutes)


@router.post("/users", response_model=UserResponse, status_code=201)
def create_user(
    payload: UserCreateRequest,
    db: Session = Depends(get_db_session),
    _: CurrentUser = Depends(require_role(Role.ADMIN)),
):
    """User provisioning is admin-only — there is no public self-signup on
    an internal enterprise data tool."""
    users = UserRepository(db)
    if users.get_by_username(payload.username) or users.get_by_email(payload.email):
        raise ValidationAppError("A user with that username or email already exists.")

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    users.add(user)
    return user


@router.get("/me", response_model=UserResponse)
def get_me(db: Session = Depends(get_db_session), current: CurrentUser = Depends(get_current_user)):
    users = UserRepository(db)
    user = users.get(current.id)
    if user is None:
        raise AuthenticationError("User no longer exists.")
    return user


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(current: CurrentUser = Depends(get_current_user)):
    """
    Issue a fresh token for a still-valid session.

    The frontend calls this automatically to extend a session before it
    expires, avoiding 401 errors on long-running monitoring pages.
    The old token must still be valid to use this endpoint.
    """
    settings = get_settings()
    token = create_access_token(
        subject=current.id,
        role=current.role,
        extra_claims={"username": current.username},
    )
    return TokenResponse(
        access_token=token,
        expires_in_minutes=settings.jwt_access_token_expire_minutes,
    )


# ── Internal helpers ──────────────────────────────────────────────────────────

def _record_login(
    db: Session,
    username: str,
    user_id: str | None,
    success: bool,
    ip: str | None,
    ua: str,
    device: str,
    reason: str | None = None,
) -> None:
    """Persist a login event and publish a security notification on failure."""
    try:
        from app.models.login_event import LoginEvent
        db.add(LoginEvent(
            username=username,
            user_id=user_id,
            success=success,
            ip_address=ip,
            user_agent=ua[:512] if ua else None,
            device_type=device,
            failure_reason=reason,
        ))
        db.flush()   # write within the existing transaction
    except Exception as exc:
        # Never let audit logging break the auth flow
        import logging
        logging.getLogger(__name__).warning("Could not record login event: %s", exc)

    if not success:
        from app.core.event_bus import publish_event_sync
        publish_event_sync(
            source="security",
            event_type="login_failed",
            severity="warning",
            title=f"Failed login: {username}",
            message=f"Authentication failed for '{username}' from IP {ip or 'unknown'}.",
            metadata={"username": username, "ip_address": ip, "reason": reason, "user_agent": ua[:200] if ua else ""},
            user_id=user_id,
        )
