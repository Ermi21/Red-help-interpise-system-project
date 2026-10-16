from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.conversation import Conversation, Message
from app.repositories.base_repository import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self, session: Session):
        super().__init__(session, Conversation)

    def get_with_messages(self, conversation_id: str) -> Conversation | None:
        stmt = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_for_user(self, user_id: str, limit: int = 50) -> list[Conversation]:
        stmt = select(Conversation).where(Conversation.user_id == user_id).limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def add_message(self, conversation_id: str, role: str, content: str, metadata: dict | None = None) -> Message:
        message = Message(conversation_id=conversation_id, role=role, content=content, metadata_json=metadata or {})
        self.session.add(message)
        self.session.flush()
        return message
