from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Workspace
from app.schemas import WorkspaceCreate, WorkspaceResponse


router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceResponse])
def list_workspaces(db: Session = Depends(get_db)) -> list[Workspace]:
    return list(db.scalars(select(Workspace).order_by(Workspace.created_at.desc())))


@router.post("", response_model=WorkspaceResponse, status_code=201)
def create_workspace(request: WorkspaceCreate, db: Session = Depends(get_db)) -> Workspace:
    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Workspace name cannot be empty")

    workspace = Workspace(name=name[:120])
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


@router.delete("/{workspace_id}", status_code=204)
def delete_workspace(workspace_id: UUID, db: Session = Depends(get_db)) -> None:
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    db.delete(workspace)
    db.commit()
