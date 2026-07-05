from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Document, ProcessingStatus, Workspace
from app.schemas import ChatRequest, ChatResponse
from app.services.qa_service import QAService


router = APIRouter(prefix="/workspaces/{workspace_id}/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def ask_question(workspace_id: UUID, request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    ready_count = (
        db.query(Document)
        .filter(Document.workspace_id == workspace_id, Document.status == ProcessingStatus.ready)
        .count()
    )
    if ready_count == 0:
        raise HTTPException(status_code=409, detail="No processed documents are ready yet")

    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    return QAService().answer(db, workspace_id, request.question.strip())
