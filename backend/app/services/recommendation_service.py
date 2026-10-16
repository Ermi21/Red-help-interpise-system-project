"""
Recommendation engine.

Recommendations in this system are generated as a byproduct of health
analysis (each detected issue already carries a `recommendation` string —
see app.monitoring.health_analyzer). This service simply re-shapes and
optionally re-runs that analysis for the /recommendations endpoint, kept
separate from HealthService so recommendations can be requested without
implying a full alert-dispatch cycle.
"""
from sqlalchemy.engine import Engine

from app.monitoring.health_analyzer import analyze_health
from app.schemas.health_schema import RecommendationResponse


class RecommendationService:
    def __init__(self, target_engine: Engine):
        self.target_engine = target_engine

    def get_recommendations(self) -> list[RecommendationResponse]:
        report = analyze_health(self.target_engine)
        return [
            RecommendationResponse(
                issue=issue["description"],
                severity=issue["severity"],
                recommendation=issue["recommendation"],
                category=issue["category"],
            )
            for issue in report["issues"]
        ]
