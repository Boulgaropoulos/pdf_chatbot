import shutil
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.db import get_db
from app.models import Document, ProcessingJob, Workspace
from app.schemas import DocumentResponse, UploadResponse


router = APIRouter(prefix="/workspaces/{workspace_id}/documents", tags=["documents"])


@router.post("", response_model=UploadResponse, status_code=201)
def upload_documents(
    workspace_id: UUID,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
) -> UploadResponse:
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    upload_root = Path(get_settings().upload_dir)
    upload_root.mkdir(parents=True, exist_ok=True)

    documents: list[Document] = []
    for file in files:
        if file.content_type != "application/pdf" and not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"{file.filename} is not a PDF")

        safe_filename = Path(file.filename).name
        storage_name = f"{uuid4()}-{safe_filename}"
        storage_path = upload_root / storage_name

        with storage_path.open("wb") as target:
            shutil.copyfileobj(file.file, target)

        document = Document(
            workspace_id=workspace.id,
            filename=safe_filename,
            storage_path=str(storage_path),
        )
        job = ProcessingJob(document=document)
        db.add(document)
        db.add(job)
        documents.append(document)

    db.commit()

    for document in documents:
        db.refresh(document)

    return UploadResponse(documents=documents)


@router.get("", response_model=list[DocumentResponse])
def list_documents(workspace_id: UUID, db: Session = Depends(get_db)) -> list[Document]:
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    return list(
        db.scalars(
            select(Document)
            .where(Document.workspace_id == workspace_id)
            .options(selectinload(Document.job))
            .order_by(Document.uploaded_at.desc())
        )
    )

