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
async def login(
    request: Request,
    db: Session = Depends(get_db_session),
):
    username = None
    password = None
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            username = body.get("username")
            password = body.get("password")
        except Exception:
            pass
    else:
        try:
            form = await request.form()
            username = form.get("username")
            password = form.get("password")
        except Exception:
            pass

    if not username or not password:
        raise AuthenticationError("Invalid username or password.")

    users = UserRepository(db)
    user = users.get_by_username(username) or users.get_by_email(username)
    if user is None or not user.is_active or not verify_password(password, user.hashed_password):
        raise AuthenticationError("Invalid username or password.")

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
