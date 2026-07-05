from dataclasses import dataclass

from app.services.pdf_parser import ParsedPage


@dataclass(frozen=True)
class TextChunk:
    page_number: int
    text: str


def chunk_pages(pages: list[ParsedPage], chunk_size: int = 450, overlap: int = 80) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    step = max(chunk_size - overlap, 1)

    for page in pages:
        words = page.text.split()
        if not words:
            continue

        for start in range(0, len(words), step):
            window = words[start : start + chunk_size]
            if not window:
                continue
            chunks.append(TextChunk(page_number=page.page_number, text=" ".join(window)))
            if start + chunk_size >= len(words):
                break

    return chunks

