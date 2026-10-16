from sqlalchemy.orm import Session

from app.chatbot.rag_pipeline import run_rag_query
from app.models.conversation import Conversation, Message
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.chat_schema import ChatResponse, SourceReference
from app.utils.exceptions import ResourceNotFoundError


class ChatService:
    def __init__(self, session: Session):
        self.session = session
        self.conversations = ConversationRepository(session)

    def send_message(
        self,
        user_id: str,
        message: str,
        conversation_id: str | None,
        domain: str = "database",
    ) -> ChatResponse:
        # Load or create conversation
        if conversation_id:
            conversation = self.conversations.get(conversation_id)
            if conversation is None or conversation.user_id != user_id:
                raise ResourceNotFoundError("Conversation not found.")
        else:
            conversation = Conversation(user_id=user_id, title=message[:60])
            conversation = self.conversations.add(conversation)

        # Build conversation history for multi-turn context
        history: list[dict] = []
        try:
            existing = self.conversations.get_with_messages(conversation.id)
            if existing and existing.messages:
                # Take last 10 messages for context
                for msg in existing.messages[-10:]:
                    history.append({"role": msg.role, "content": msg.content})
        except Exception:
            pass  # history is best-effort

        # Record user message
        self.conversations.add_message(conversation.id, role="user", content=message)

        # Run RAG pipeline with history for multi-turn context
        result = run_rag_query(
            question=message,
            domain=domain,
            history=history,
        )

        # Record assistant response with full metadata
        self.conversations.add_message(
            conversation.id,
            role="assistant",
            content=result.answer,
            metadata={
                "generated_sql": result.generated_sql,
                "row_count": result.row_count,
                "sources": result.sources,
            },
        )

        return ChatResponse(
            conversation_id=conversation.id,
            answer=result.answer,
            generated_sql=result.generated_sql,
            row_count=result.row_count,
            sources=[SourceReference(**s) for s in result.sources],
        )

    def get_conversation(self, user_id: str, conversation_id: str) -> Conversation:
        conversation = self.conversations.get_with_messages(conversation_id)
        if conversation is None or conversation.user_id != user_id:
            raise ResourceNotFoundError("Conversation not found.")
        return conversation

    def list_conversations(self, user_id: str) -> list[Conversation]:
        return self.conversations.list_for_user(user_id)

    def delete_conversation(self, user_id: str, conversation_id: str) -> None:
        conversation = self.conversations.get(conversation_id)
        if conversation is None or conversation.user_id != user_id:
            raise ResourceNotFoundError("Conversation not found.")
        self.conversations.delete(conversation_id)
