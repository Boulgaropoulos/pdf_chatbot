from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models import ProcessingStatus


class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceCreate(BaseModel):
    name: str


class JobResponse(BaseModel):
    id: UUID
    document_id: UUID
    status: ProcessingStatus
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    filename: str
    status: ProcessingStatus
    uploaded_at: datetime
    job: JobResponse | None = None

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    documents: list[DocumentResponse]


class ChatRequest(BaseModel):
    question: str


class Citation(BaseModel):
    filename: str
    page: int


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
