from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.utils.exceptions import AppException
from app.utils.logger import get_logger

logger = get_logger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error_code": exc.error_code, "message": exc.message, "details": exc.details},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        # Framework-raised HTTPExceptions (e.g. OAuth2PasswordBearer's own
        # "Not authenticated" when no Authorization header is present at
        # all) bypass our AppException hierarchy entirely and would
        # otherwise return FastAPI's default {"detail": "..."} shape —
        # normalized here so every error response the frontend sees has
        # the same {error_code, message, details} contract.
        error_code = {401: "authentication_error", 403: "authorization_error", 404: "not_found"}.get(
            exc.status_code, "http_error"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"error_code": error_code, "message": str(exc.detail), "details": {}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error_code": "validation_error",
                "message": "The request body failed validation.",
                "details": {"errors": exc.errors()},
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"error_code": "internal_error", "message": "An unexpected error occurred.", "details": {}},
        )
