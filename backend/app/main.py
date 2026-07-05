from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, documents, jobs, workspaces
from app.config import get_settings
from app.db import init_db


settings = get_settings()

app = FastAPI(title="PDF Document QA API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(workspaces.router)
app.include_router(documents.router)
app.include_router(jobs.router)
app.include_router(chat.router)

