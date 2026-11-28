# Import all ORM models so Base.metadata is fully populated before create_all().
# Add new models here as they are created.
from app.models import (  # noqa: F401
    alert,
    audit_log,
    conversation,
    llm_usage,
    login_event,
    metadata,
    notification,
    system_metrics,
    user,
    user_profile,
)
