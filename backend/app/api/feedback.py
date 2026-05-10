"""Message feedback endpoints."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_auth
from app.models.user import User
from app.models.conversation import Conversation, ConversationMessage
from app.models.feedback import MessageFeedback
from app.schemas.conversation import FeedbackRequest

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.post("")
async def submit_feedback(
    request: FeedbackRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Upsert like/dislike feedback for a message."""
    if request.rating not in ("like", "dislike"):
        raise HTTPException(status_code=400, detail="Rating must be 'like' or 'dislike'")

    message = db.query(ConversationMessage).join(Conversation).filter(
        ConversationMessage.id == request.message_id,
        Conversation.user_id == user.id,
    ).first()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    existing = db.query(MessageFeedback).filter(
        MessageFeedback.message_id == request.message_id
    ).first()

    if existing:
        existing.rating = request.rating
        existing.updated_at = datetime.utcnow()
    else:
        feedback = MessageFeedback(
            message_id=request.message_id,
            user_id=user.id,
            rating=request.rating,
        )
        db.add(feedback)

    db.commit()
    return {"success": True, "rating": request.rating}


@router.delete("/{message_id}")
async def remove_feedback(
    message_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Remove feedback for a message (toggle off)."""
    feedback = db.query(MessageFeedback).join(ConversationMessage).join(Conversation).filter(
        MessageFeedback.message_id == message_id,
        Conversation.user_id == user.id,
    ).first()

    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    db.delete(feedback)
    db.commit()

    return {"success": True}
