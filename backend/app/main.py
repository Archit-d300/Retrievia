from __future__ import annotations

import json

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from . import config, papers
from .graph import build_graph
from .store import get_store

app = FastAPI(title="Retrievia API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    doc_ids: list[str] | None = None
    use_web: bool = True
    history: list[dict] = Field(default_factory=list)


class PaperRequest(BaseModel):
    doc_ids: list[str] | None = None


def _state(req: ChatRequest) -> dict:
    return {"question": req.question.strip(), "doc_ids": req.doc_ids or None, "use_web": req.use_web,
            "history": [{"role": m.get("role", "user"), "content": str(m.get("content", ""))} for m in req.history[-6:]]}


@app.get("/api/health")
def health():
    return {"status": "ok", "llm": config.LLM_MODEL, "grader": config.GRADER_MODEL,
            "embeddings": f"{config.EMBED_MODEL} ({config.EMBED_MODE})", "hf_token_set": bool(config.HF_TOKEN)}


@app.get("/api/documents")
def list_documents():
    return get_store().list()


@app.post("/api/documents", status_code=201)
async def upload_document(file: UploadFile = File(...), kind: str = Form("notes")):
    data = await file.read()
    if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {config.MAX_UPLOAD_MB} MB")
    try:
        return get_store().add_document(file.filename or "upload", data, kind)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: str):
    if not get_store().delete(doc_id):
        raise HTTPException(404, "Document not found")
    return {"deleted": doc_id}


@app.post("/api/chat")
def chat(req: ChatRequest):
    out = build_graph().invoke(_state(req))
    return {k: out.get(k) for k in ("answer", "sources", "steps", "tokens", "verdict", "mode")}


@app.post("/api/chat/stream")
def chat_stream(req: ChatRequest):
    """Server-Sent Events: one `step` event per agent node as it finishes, then a `final` event."""

    def gen():
        final: dict = {"steps": [], "tokens": 0}
        try:
            for update in build_graph().stream(_state(req), stream_mode="updates"):
                for node, part in update.items():
                    for st in part.get("steps", []):
                        yield f"data: {json.dumps({'type': 'step', **st})}\n\n"
                    for k, v in part.items():
                        if k == "tokens":
                            final["tokens"] += v
                        elif k != "steps":
                            final[k] = v
            payload = {k: final.get(k) for k in ("answer", "sources", "tokens", "verdict", "mode")}
            yield f"data: {json.dumps({'type': 'final', **payload})}\n\n"
        except Exception as e:  # surface model/provider errors to the UI instead of a dead stream
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)[:300]})}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/analyze/papers")
def analyze_papers(req: PaperRequest):
    return papers.analyze(get_store(), req.doc_ids)
