from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user, get_db_session
from app.schemas.chat_schema import ChatRequest, ChatResponse, ConversationResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
def send_message(payload: ChatRequest, db: Session = Depends(get_db_session), current: CurrentUser = Depends(get_current_user)):
    service = ChatService(db)
    return service.send_message(
        user_id=current.id,
        message=payload.message,
        conversation_id=payload.conversation_id,
        domain=payload.domain or "database"
    )


@router.get("/conversations", response_model=list[ConversationResponse])
def list_conversations(db: Session = Depends(get_db_session), current: CurrentUser = Depends(get_current_user)):
    service = ChatService(db)
    return service.list_conversations(current.id)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def get_conversation(conversation_id: str, db: Session = Depends(get_db_session), current: CurrentUser = Depends(get_current_user)):
    service = ChatService(db)
    return service.get_conversation(current.id, conversation_id)
