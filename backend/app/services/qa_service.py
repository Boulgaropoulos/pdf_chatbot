from uuid import UUID

from sqlalchemy.orm import Session

from app.schemas import ChatResponse, Citation
from app.services.llm_service import LLMService, UNKNOWN_ANSWER
from app.services.retriever import RetrievedChunk, Retriever


class QAService:
    def __init__(self) -> None:
        self.retriever = Retriever()
        self.llm_service = LLMService()

    def answer(self, db: Session, workspace_id: UUID, question: str) -> ChatResponse:
        chunks = self.retriever.search(db, workspace_id, question)
        if is_overview_question(question):
            chunks = merge_chunks(self.retriever.initial_chunks(db, workspace_id), chunks)
        if not chunks:
            return ChatResponse(answer=UNKNOWN_ANSWER, citations=[])

        grounded_answer = self.llm_service.answer_from_context(question, chunks)
        if UNKNOWN_ANSWER.lower() in grounded_answer.answer.lower():
            return ChatResponse(answer=UNKNOWN_ANSWER, citations=[])

        cited_chunks = select_cited_chunks(chunks, grounded_answer.source_indexes)
        return ChatResponse(answer=grounded_answer.answer, citations=dedupe_citations(cited_chunks))


def dedupe_citations(chunks: list[RetrievedChunk]) -> list[Citation]:
    citations: list[Citation] = []
    seen: set[tuple[str, int]] = set()

    for chunk in chunks:
        key = (chunk.filename, chunk.page_number)
        if key in seen:
            continue
        seen.add(key)
        citations.append(Citation(filename=chunk.filename, page=chunk.page_number))
        if len(citations) >= 6:
            break

    return citations


def select_cited_chunks(chunks: list[RetrievedChunk], source_indexes: list[int]) -> list[RetrievedChunk]:
    selected: list[RetrievedChunk] = []
    for source_index in source_indexes:
        chunk_index = source_index - 1
        if 0 <= chunk_index < len(chunks):
            selected.append(chunks[chunk_index])
    return selected or chunks[:3]


def merge_chunks(*chunk_groups: list[RetrievedChunk]) -> list[RetrievedChunk]:
    merged: list[RetrievedChunk] = []
    seen: set[UUID] = set()

    for group in chunk_groups:
        for chunk in group:
            if chunk.chunk_id in seen:
                continue
            seen.add(chunk.chunk_id)
            merged.append(chunk)

    return merged


def is_overview_question(question: str) -> bool:
    normalized = question.lower()
    overview_terms = [
        "about",
        "overview",
        "summarize",
        "summary",
        "what is this document",
        "what are these documents",
        "chapters",
        "chapter",
        "contents",
        "table of contents",
    ]
    return any(term in normalized for term in overview_terms)
