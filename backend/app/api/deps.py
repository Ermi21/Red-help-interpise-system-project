from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.auth.jwt_handler import decode_access_token
from app.auth.rbac import Role, role_satisfies
from app.config.settings import Settings, get_settings
from app.database.connection import get_app_db, get_target_engine
from app.utils.exceptions import AuthorizationError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class CurrentUser:
    def __init__(self, user_id: str, username: str, role: str):
        self.id = user_id
        self.username = username
        self.role = role


def get_current_user(token: str = Depends(oauth2_scheme)) -> CurrentUser:
    payload = decode_access_token(token)
    return CurrentUser(user_id=payload["sub"], username=payload.get("username", payload["sub"]), role=payload.get("role", "viewer"))


def require_role(minimum_role: Role):
    def _dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not role_satisfies(user.role, minimum_role):
            raise AuthorizationError(f"This action requires the '{minimum_role.value}' role or higher.")
        return user

    return _dependency


def get_db_session() -> Session:
    yield from get_app_db()


def get_readonly_engine() -> Engine:
    return get_target_engine()


def get_app_settings() -> Settings:
    return get_settings()
