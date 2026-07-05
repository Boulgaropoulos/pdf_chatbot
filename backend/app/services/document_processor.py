from sqlalchemy.orm import Session

from app.models import Document, DocumentChunk
from app.services.chunker import chunk_pages
from app.services.embedding_service import EmbeddingService
from app.services.pdf_parser import parse_pdf


def process_document(db: Session, document: Document) -> int:
    pages = parse_pdf(document.storage_path)
    if not pages:
        raise ValueError("No extractable text found in PDF")

    chunks = chunk_pages(pages)
    if not chunks:
        raise ValueError("No text chunks could be created from PDF")

    embedding_service = EmbeddingService()
    embeddings = embedding_service.embed_texts([chunk.text for chunk in chunks])

    for chunk, embedding in zip(chunks, embeddings, strict=True):
        db.add(
            DocumentChunk(
                document_id=document.id,
                page_number=chunk.page_number,
                chunk_text=chunk.text,
                embedding=embedding,
            )
        )

    return len(chunks)

