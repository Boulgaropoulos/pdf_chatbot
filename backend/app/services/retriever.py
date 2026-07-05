from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document, DocumentChunk, ProcessingStatus
from app.services.embedding_service import EmbeddingService


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: UUID
    document_id: UUID
    filename: str
    page_number: int
    text: str
    score: float


class Retriever:
    def __init__(self) -> None:
        self.embedding_service = EmbeddingService()

    def search(self, db: Session, workspace_id: UUID, question: str, limit: int = 6) -> list[RetrievedChunk]:
        query_embedding = self.embedding_service.embed_query(question)
        distance = DocumentChunk.embedding.cosine_distance(query_embedding).label("distance")

        rows = db.execute(
            select(DocumentChunk, Document.filename, distance)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                Document.workspace_id == workspace_id,
                Document.status == ProcessingStatus.ready,
                DocumentChunk.embedding.is_not(None),
            )
            .order_by(distance)
            .limit(limit)
        ).all()

        return [
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                filename=filename,
                page_number=chunk.page_number,
                text=chunk.chunk_text,
                score=float(distance_value),
            )
            for chunk, filename, distance_value in rows
        ]

    def initial_chunks(self, db: Session, workspace_id: UUID, per_document: int = 4) -> list[RetrievedChunk]:
        documents = db.scalars(
            select(Document)
            .where(Document.workspace_id == workspace_id, Document.status == ProcessingStatus.ready)
            .order_by(Document.uploaded_at)
        ).all()

        chunks: list[RetrievedChunk] = []
        for document in documents:
            rows = db.scalars(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == document.id)
                .order_by(DocumentChunk.page_number, DocumentChunk.created_at)
                .limit(per_document)
            ).all()
            chunks.extend(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    filename=document.filename,
                    page_number=chunk.page_number,
                    text=chunk.chunk_text,
                    score=0.0,
                )
                for chunk in rows
            )

        return chunks
