"""Previous-year paper analysis. Zero LLM tokens: question splitting + embedding clustering + retrieval."""
from __future__ import annotations

import re

import numpy as np

from . import config
from .models import get_embeddings
from .store import Store

_QSPLIT = re.compile(r"(?m)^\s*(?:Q(?:uestion)?\.?\s*\d+[.):]?|\(?\d{1,2}[.)]|\([a-h]\))\s+")


def extract_questions(text: str) -> list[str]:
    parts = _QSPLIT.split(text)
    qs = [re.sub(r"\s+", " ", p).strip() for p in parts]
    return [q[:600] for q in qs if 25 <= len(q)]


def analyze(store: Store, doc_ids: list[str] | None = None, top: int = 12) -> dict:
    papers = [m for m in store.list() if m["kind"] == "paper" and (not doc_ids or m["id"] in doc_ids)]
    study_ids = [m["id"] for m in store.list() if m["kind"] != "paper"]
    items: list[tuple[str, str]] = []
    for p in papers:
        text = "\n".join(t for _, t in store.pages(p["id"]))
        items += [(p["name"], q) for q in extract_questions(text)]
    if not items:
        return {"papers": len(papers), "questions": 0, "topics": []}

    vecs = np.asarray(get_embeddings().embed_documents([q for _, q in items]), dtype="float32")
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-9

    clusters: list[dict] = []  # greedy centroid clustering
    for i, v in enumerate(vecs):
        best, best_sim = None, config.PAPER_SIM_THRESHOLD
        for c in clusters:
            sim = float(v @ (c["sum"] / np.linalg.norm(c["sum"])))
            if sim >= best_sim:
                best, best_sim = c, sim
        if best is None:
            clusters.append({"sum": v.copy(), "idx": [i]})
        else:
            best["sum"] += v
            best["idx"].append(i)

    total = len(items)
    topics = []
    for c in sorted(clusters, key=lambda c: len(c["idx"]), reverse=True)[:top]:
        qs = [items[i] for i in c["idx"]]
        rep = min(qs, key=lambda x: len(x[1]))[1]
        study = []
        if study_ids:
            for d, s in store.search(rep, study_ids, k=2):
                if s < config.GRADE_LOW:  # don't point students at unrelated pages
                    continue
                study.append({"source": d.metadata["source"], "page": d.metadata.get("page"),
                              "section": d.metadata.get("section") or None, "score": round(s, 3)})
        topics.append({
            "topic": rep[:160], "count": len(qs), "weightage": round(100 * len(qs) / total, 1),
            "papers": sorted({n for n, _ in qs}), "examples": [q[:200] for _, q in qs[:3]], "study": study,
        })
    return {"papers": len(papers), "questions": total, "topics": topics}


def to_markdown(res: dict) -> str:
    if not res["questions"]:
        return "I couldn't find any question papers to analyse. Upload previous-year papers and mark them as **paper**."
    lines = [f"Analysed **{res['questions']} questions** across **{res['papers']} paper(s)**. Most repeated topics:\n"]
    for i, t in enumerate(res["topics"][:8], 1):
        where = "; ".join(
            f"{s['source']}" + (f" p.{s['page']}" if s["page"] else "") + (f" — {s['section']}" if s["section"] else "")
            for s in t["study"]
        )
        lines.append(f"{i}. **{t['topic']}** — asked {t['count']}× (~{t['weightage']}%)" + (f"  \n   _Study:_ {where}" if where else ""))
    return "\n".join(lines)
