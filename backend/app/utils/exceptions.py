"""
Application exception hierarchy.

Using typed exceptions (instead of raising HTTPException deep inside
services/repositories) keeps the domain layer framework-agnostic. The
`app.middleware.error_handler` module maps each of these to an HTTP
response at the edge of the application.
"""


class AppException(Exception):
    """Base class for all application-raised exceptions."""

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str, *, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AuthenticationError(AppException):
    status_code = 401
    error_code = "authentication_error"


class AuthorizationError(AppException):
    status_code = 403
    error_code = "authorization_error"


class ResourceNotFoundError(AppException):
    status_code = 404
    error_code = "not_found"


class ValidationAppError(AppException):
    status_code = 422
    error_code = "validation_error"


class RateLimitExceededError(AppException):
    status_code = 429
    error_code = "rate_limit_exceeded"


class DatabaseReadOnlyViolationError(AppException):
    """Raised whenever any code path attempts a non-SELECT operation
    against the protected target database. This should never legitimately
    fire — if it does, something upstream failed to validate correctly."""

    status_code = 403
    error_code = "readonly_violation"


class UnsafeSQLError(AppException):
    """Raised when generated or supplied SQL fails the safety validator."""

    status_code = 400
    error_code = "unsafe_sql"


class LLMProviderError(AppException):
    status_code = 502
    error_code = "llm_provider_error"


class VectorStoreError(AppException):
    status_code = 502
    error_code = "vector_store_error"


class PromptInjectionDetectedError(AppException):
    status_code = 400
    error_code = "prompt_injection_detected"
