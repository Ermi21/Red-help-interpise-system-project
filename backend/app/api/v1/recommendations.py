from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, get_readonly_engine, require_role
from app.auth.rbac import Role
from app.schemas.health_schema import RecommendationResponse
from app.services.recommendation_service import RecommendationService
from sqlalchemy.engine import Engine

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get("", response_model=list[RecommendationResponse])
def get_recommendations(
    engine: Engine = Depends(get_readonly_engine),
    _: CurrentUser = Depends(require_role(Role.VIEWER)),
):
    """AI-generated recommendations derived from the latest health
    analysis. Recommendations are informational only and are never
    executed automatically."""
    return RecommendationService(engine).get_recommendations()
