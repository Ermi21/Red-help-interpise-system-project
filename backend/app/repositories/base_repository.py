"""Generic repository base class (Repository Pattern) over the app's own
operational database. Keeps SQLAlchemy Session usage out of the service
layer so services depend on repository interfaces, not the ORM directly."""
from typing import Generic, Type, TypeVar

from sqlalchemy.orm import Session

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    def __init__(self, session: Session, model: Type[ModelType]):
        self.session = session
        self.model = model

    def get(self, id_: str) -> ModelType | None:
        return self.session.get(self.model, id_)

    def list(self, limit: int = 100, offset: int = 0) -> list[ModelType]:
        return self.session.query(self.model).offset(offset).limit(limit).all()

    def add(self, instance: ModelType) -> ModelType:
        self.session.add(instance)
        self.session.flush()
        return instance

    def delete(self, instance: ModelType) -> None:
        self.session.delete(instance)
        self.session.flush()
