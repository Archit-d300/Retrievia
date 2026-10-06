"""Corrective RAG as a LangGraph state machine.

route ─┬─ qa ────► rewrite ► retrieve ► grade ─┬─ correct ─────────────────────► generate
       │                                       └─ ambiguous/incorrect ► web ───► generate
       ├─ summarize ───────────────────────────────────────────────────────────► END
       └─ analyze (paper trends) ──────────────────────────────────────────────► END

Token-saving design: rule-based routing, rewrite only when there is chat history, score-gated grading
(the LLM only sees *ambiguous* chunks, in ONE batched call with a tiny JSON output), truncated context,
hard max_tokens, and zero-LLM paper analysis.
"""
from __future__ import annotations

import json
import operator
import re
from functools import lru_cache
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from . import config, papers
from .models import get_grader, get_llm
from .store import get_store

TRUSTED = ("wikipedia.org", "geeksforgeeks.org", "khanacademy.org", "britannica.com", "ocw.mit.edu",
           "tutorialspoint.com", "nptel.ac.in", "openstax.org", "arxiv.org", ".edu", ".ac.in", ".ac.uk")
SUM_RE = re.compile(r"\b(summar(y|ise|ize|ies)|revision notes?|key points|exam guide|cheat ?sheet|tl;?dr)\b", re.I)
PAPER_RE = re.compile(
    r"\b(previous[- ]year|past (year )?papers?|question papers?|frequently asked|repeated(ly)?|most asked|weightage|important topics)\b", re.I)


class State(TypedDict, total=False):
    question: str
    history: list[dict]
    doc_ids: list[str] | None
    use_web: bool
    mode: str
    query: str
    docs: list[dict]
    verdict: str
    answer: str
    sources: list[dict]
    steps: Annotated[list[dict], operator.add]
    tokens: Annotated[int, operator.add]


def _step(node: str, detail: str) -> dict:
    return {"steps": [{"node": node, "detail": detail}]}


def _doc(d, score: float) -> dict:
    m = d.metadata
    return {"text": d.page_content, "source": m["source"], "page": m.get("page"), "section": m.get("section") or None,
            "doc_id": m["doc_id"], "kind": m.get("kind"), "score": round(score, 3), "origin": "local"}


def _label(d: dict) -> str:
    if d["origin"] == "web":
        return f"{d['source']} ({d['url']})"
    return d["source"] + (f", p.{d['page']}" if d.get("page") else "") + (f", {d['section']}" if d.get("section") else "")


def _sources(docs: list[dict]) -> list[dict]:
    return [{"n": i, "label": _label(d), "source": d["source"], "page": d.get("page"), "section": d.get("section"),
             "origin": d["origin"], "url": d.get("url"), "score": d.get("score"), "snippet": d["text"][:220]}
            for i, d in enumerate(docs, 1)]


# ------------------------------------------------------------------ nodes
def route(s: State):
    q = s["question"]
    mode = "analyze" if PAPER_RE.search(q) else "summarize" if SUM_RE.search(q) else "qa"
    return {"mode": mode, **_step("route", f"intent → {mode}")}


def rewrite(s: State):
    hist = s.get("history") or []
    if not hist:
        return {"query": s["question"], **_step("rewrite", "no history, query kept as-is (0 tokens)")}
    convo = "\n".join(f"{m['role']}: {m['content'][:300]}" for m in hist[-4:])
    text, tok = get_llm().chat(
        "Rewrite the last user question as one standalone search query. Output only the query.",
        f"{convo}\nuser: {s['question']}", max_tokens=48, temperature=0)
    q = text.strip().strip('"') or s["question"]
    return {"query": q, "tokens": tok, **_step("rewrite", f"standalone query: “{q}”")}


def retrieve(s: State):
    store = get_store()
    # Past papers hold questions, not explanations: only search them if the user explicitly selected them.
    ids = s.get("doc_ids") or [m["id"] for m in store.list() if m["kind"] != "paper"] or None
    hits = store.search(s["query"], ids, k=config.RETRIEVE_K)
    docs = [_doc(d, sc) for d, sc in hits]
    return {"docs": docs, **_step("retrieve", f"{len(docs)} chunks from your material")}


def _llm_grade(question: str, docs: list[dict]) -> tuple[list[bool], int]:
    listing = "\n".join(f"{i}. {d['text'][:350]!r}" for i, d in enumerate(docs))
    text, tok = get_grader().chat(
        'For each numbered passage decide if it helps answer the question. Reply ONLY JSON like {"relevant":[1,0]}.',
        f"Question: {question}\n\nPassages:\n{listing}", max_tokens=16 + 4 * len(docs), temperature=0)
    m = re.search(r"\[[\d,\s]*\]", text)
    flags = json.loads(m.group(0)) if m else []
    if len(flags) != len(docs):  # malformed output → keep them (fail-open, never lose context)
        return [True] * len(docs), tok
    return [bool(f) for f in flags], tok


def grade(s: State):
    """CRAG evaluator. Score-gated: only ambiguous chunks are graded by the LLM."""
    docs, tokens = s.get("docs", []), 0
    kept = [d for d in docs if d["score"] >= config.GRADE_HIGH]
    gray = [d for d in docs if config.GRADE_LOW <= d["score"] < config.GRADE_HIGH]
    if gray and len(kept) < config.CONTEXT_K:
        flags, tokens = _llm_grade(s["query"], gray)
        kept += [d for d, ok in zip(gray, flags) if ok]
    kept = sorted(kept, key=lambda d: -d["score"])[: config.CONTEXT_K]
    verdict = "correct" if len(kept) >= 2 else "ambiguous" if kept else "incorrect"
    return {"docs": kept, "verdict": verdict, "tokens": tokens,
            **_step("grade", f"{verdict.upper()} — kept {len(kept)}/{len(docs)} chunks"
                             f" ({'LLM-graded ' + str(len(gray)) if tokens else 'no LLM needed'})")}


def web_search(s: State):
    from ddgs import DDGS

    try:
        raw = list(DDGS().text(s["query"], max_results=8))
    except Exception as e:  # network / rate limit → degrade gracefully
        return {**_step("web_search", f"web unavailable ({type(e).__name__}); using local material only")}
    raw.sort(key=lambda r: not any(t in r.get("href", "") for t in TRUSTED))  # trusted educational sites first
    web = [{"text": r.get("body", "")[:600], "source": r.get("title", "web")[:80], "url": r.get("href"), "page": None,
            "section": None, "score": None, "origin": "web", "doc_id": None} for r in raw[:3]]
    docs = s.get("docs", []) + web
    return {"docs": docs, **_step("web_search", f"added {len(web)} web sources (trusted sites ranked first)")}


def generate(s: State):
    docs = s.get("docs", [])
    if not docs:
        msg = ("I couldn't find this in your uploaded material" + ("" if s.get("use_web") else " (web search is off)")
               + ". Try uploading the relevant notes/textbook or rephrasing.")
        return {"answer": msg, "sources": [], **_step("generate", "no grounded context → declined (0 tokens)")}
    ctx = "\n\n".join(f"[{i}] ({_label(d)})\n{d['text']}" for i, d in enumerate(docs, 1))
    text, tok = get_llm().chat(
        "You are a study assistant. Answer ONLY from the numbered context. Cite sources like [1]. "
        "Be concise and exam-oriented. If the context is insufficient, say so.",
        f"Question: {s['question']}\n\nContext:\n{ctx}", max_tokens=450)
    return {"answer": text, "sources": _sources(docs), "tokens": tok, **_step("generate", f"answered using {len(docs)} sources")}


def summarize(s: State):
    store, ids = get_store(), s.get("doc_ids")
    pool = [m["id"] for m in store.list() if m["kind"] != "paper" and (not ids or m["id"] in ids)] or ids
    picked: list[dict] = []
    hits = [(d, sc) for d, sc in store.search(s["question"], pool, k=10) if sc >= config.GRADE_LOW] if pool else []
    if len(hits) >= 4:
        picked = [_doc(d, sc) for d, sc in hits]
    else:  # whole-document request → evenly sample chunks across the document
        for did in pool or []:
            pages = store.pages(did)
            name = store.registry[did]["name"]
            texts = [(p, t) for p, t in pages if t.strip()]
            step = max(1, len(texts) // 8)
            picked += [{"text": t[:900], "source": name, "page": p, "section": None, "doc_id": did, "origin": "local",
                        "score": None, "kind": "notes"} for p, t in texts[::step][:8]]
    if not picked:
        return {"answer": "Upload some notes or a textbook first, then ask for a summary.", "sources": [],
                **_step("summarize", "nothing to summarise")}
    picked = picked[:10]
    ctx = "\n\n".join(f"[{i}] ({_label(d)})\n{d['text'][:900]}" for i, d in enumerate(picked, 1))
    text, tok = get_llm().chat(
        "You write revision material for students. Using ONLY the context, produce structured markdown: "
        "a 2-sentence overview, then chapter/topic-wise bullet points, then 'Likely exam questions' (3 items). "
        "Cite sources like [1]. Be concise.",
        f"Request: {s['question']}\n\nContext:\n{ctx}", max_tokens=700, temperature=0.2)
    return {"answer": text, "sources": _sources(picked), "tokens": tok,
            **_step("summarize", f"summarised from {len(picked)} representative chunks (1 LLM call)")}


def analyze(s: State):
    res = papers.analyze(get_store(), s.get("doc_ids"))
    return {"answer": papers.to_markdown(res), "sources": [],
            **_step("analyze", f"clustered {res['questions']} questions from {res['papers']} papers (0 tokens)")}


# ------------------------------------------------------------------ graph
def _after_grade(s: State) -> str:
    return "generate" if s["verdict"] == "correct" or not s.get("use_web", True) else "web_search"


@lru_cache
def build_graph():
    g = StateGraph(State)
    for name, fn in [("route", route), ("rewrite", rewrite), ("retrieve", retrieve), ("grade", grade),
                     ("web_search", web_search), ("generate", generate), ("summarize", summarize), ("analyze", analyze)]:
        g.add_node(name, fn)
    g.add_edge(START, "route")
    g.add_conditional_edges("route", lambda s: s["mode"], {"qa": "rewrite", "summarize": "summarize", "analyze": "analyze"})
    g.add_edge("rewrite", "retrieve")
    g.add_edge("retrieve", "grade")
    g.add_conditional_edges("grade", _after_grade, {"generate": "generate", "web_search": "web_search"})
    g.add_edge("web_search", "generate")
    for end in ("generate", "summarize", "analyze"):
        g.add_edge(end, END)
    return g.compile()
