import json
from dataclasses import dataclass

from openai import OpenAI

from app.config import get_settings
from app.services.retriever import RetrievedChunk


CHAT_MODEL = "gpt-4o-mini"
UNKNOWN_ANSWER = "I couldn't find an answer to that question in the uploaded documents."


@dataclass(frozen=True)
class GroundedAnswer:
    answer: str
    source_indexes: list[int]


class LLMService:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required to answer questions")
        self.client = OpenAI(api_key=settings.openai_api_key)

    def answer_from_context(self, question: str, chunks: list[RetrievedChunk]) -> GroundedAnswer:
        context = "\n\n".join(
            f"[Source {index}] File: {chunk.filename}, page {chunk.page_number}\n{chunk.text}"
            for index, chunk in enumerate(chunks, start=1)
        )

        response = self.client.chat.completions.create(
            model=CHAT_MODEL,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You answer questions using only the provided document context. "
                        "If the context does not contain the answer, reply exactly: "
                        f"{UNKNOWN_ANSWER} "
                        "If the question asks for a broad overview and multiple documents are present, "
                        "briefly cover each relevant document. "
                        "Return JSON only with this shape: "
                        '{"answer": "string", "source_indexes": [1, 2]}. '
                        "source_indexes must contain only the source numbers that directly support the answer. "
                        "If the answer is not found, use an empty source_indexes array."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Context:\n{context}\n\nQuestion: {question}",
                },
            ],
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content or "{}"
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return GroundedAnswer(answer=UNKNOWN_ANSWER, source_indexes=[])

        answer = str(parsed.get("answer", "")).strip() or UNKNOWN_ANSWER
        raw_indexes = parsed.get("source_indexes", [])
        source_indexes = [int(index) for index in raw_indexes if isinstance(index, int | float)]
        return GroundedAnswer(answer=answer, source_indexes=source_indexes)
