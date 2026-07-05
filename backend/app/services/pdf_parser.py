from dataclasses import dataclass

import fitz


@dataclass(frozen=True)
class ParsedPage:
    page_number: int
    text: str


def parse_pdf(path: str) -> list[ParsedPage]:
    pages: list[ParsedPage] = []
    with fitz.open(path) as document:
        for index, page in enumerate(document, start=1):
            text = page.get_text("text").strip()
            if text:
                pages.append(ParsedPage(page_number=index, text=text))
    return pages

