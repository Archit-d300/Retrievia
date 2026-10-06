"""End-to-end test with fake HF models (no network): upload → CRAG chat → summary → paper analysis."""
import hashlib
import json
import re

import numpy as np
import pytest
from fastapi.testclient import TestClient


class FakeEmb:
    def _v(self, t):
        v = np.zeros(512, dtype="float32")
        for w in re.findall(r"[a-z]{3,}", t.lower()):
            v[int(hashlib.md5(w.encode()).hexdigest(), 16) % 512] += 1
        return (v / (np.linalg.norm(v) + 1e-9)).tolist()

    def embed_documents(self, texts): return [self._v(t) for t in texts]
    def embed_query(self, t): return self._v(t)
    def __call__(self, t): return self._v(t)  # FAISS may call the embeddings as a function


class FakeLLM:
    calls = []
    def chat(self, system, user, max_tokens=400, temperature=0.1):
        FakeLLM.calls.append(system[:30])
        if "ONLY JSON" in system:
            n = len(re.findall(r"^\d+\.", user, re.M))
            return json.dumps({"relevant": [1] * n}), 20
        return "Deadlock needs four conditions [1].", 50


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    import importlib
    from app import config, models
    importlib.reload(config)
    config.PAPER_SIM_THRESHOLD = 0.6  # crude bag-of-words test embedder scores paraphrases lower than a real model
    for n in ("get_embeddings", "get_llm", "get_grader"):
        getattr(models, n).cache_clear()
    monkeypatch.setattr(models, "get_embeddings", lambda: FakeEmb())
    import app.store as store
    importlib.reload(store)
    monkeypatch.setattr(store, "get_embeddings", lambda: FakeEmb())
    import app.papers as papers, app.graph as graph
    importlib.reload(papers); importlib.reload(graph)
    monkeypatch.setattr(papers, "get_embeddings", lambda: FakeEmb())
    monkeypatch.setattr(graph, "get_llm", lambda: FakeLLM())
    monkeypatch.setattr(graph, "get_grader", lambda: FakeLLM())
    monkeypatch.setattr(graph, "get_store", store.get_store)
    graph.build_graph.cache_clear()
    import app.main as main
    importlib.reload(main)
    monkeypatch.setattr(main, "build_graph", graph.build_graph)
    monkeypatch.setattr(main, "get_store", store.get_store)
    monkeypatch.setattr(main.papers, "analyze", papers.analyze)
    return TestClient(main.app)


NOTES = b"""Chapter 3 Deadlocks
A deadlock occurs when processes wait forever. Four necessary conditions: mutual exclusion, hold and wait, no preemption, circular wait.
Deadlock prevention removes one of the four conditions such as circular wait by ordering resources.
"""
PAPER = b"""1. Explain deadlock prevention and the four necessary conditions for deadlock in operating systems.
2. Describe the necessary conditions of deadlock and how deadlock prevention removes them.
3. What is virtual memory and how does paging work in an operating system?
"""


def test_full_flow(client):
    assert client.get("/api/health").json()["status"] == "ok"
    n = client.post("/api/documents", files={"file": ("os.txt", NOTES)}, data={"kind": "notes"}); assert n.status_code == 201
    p = client.post("/api/documents", files={"file": ("2023.txt", PAPER)}, data={"kind": "paper"}); assert p.status_code == 201
    assert len(client.get("/api/documents").json()) == 2

    r = client.post("/api/chat", json={"question": "Explain deadlock prevention", "use_web": False}).json()
    assert r["verdict"] in ("correct", "ambiguous") and r["sources"] and "[1]" in r["answer"]
    assert all(s["source"] == "os.txt" for s in r["sources"])  # past papers aren't used as answer context
    assert all(s["section"] == "Chapter 3 Deadlocks" for s in r["sources"])

    r = client.post("/api/chat", json={"question": "quantum chromodynamics gluons", "use_web": False}).json()
    assert r["verdict"] == "incorrect" and "couldn't find" in r["answer"] and r["tokens"] == 0  # declined, no LLM spend

    r = client.post("/api/chat", json={"question": "Summarize deadlocks chapter", "use_web": False}).json()
    assert r["mode"] == "summarize" and r["answer"]

    a = client.post("/api/analyze/papers", json={}).json()
    assert a["questions"] == 3 and a["topics"][0]["count"] == 2  # the two deadlock questions cluster together
    assert a["topics"][0]["study"][0]["source"] == "os.txt"
    assert a["topics"][1]["study"] == []  # paging question has no relevant notes → no bogus pointer

    ev = client.post("/api/chat/stream", json={"question": "Explain deadlock prevention", "use_web": False}).text
    assert '"type": "step"' in ev and '"type": "final"' in ev

    assert client.delete(f"/api/documents/{n.json()['id']}").status_code == 200
    assert len(client.get("/api/documents").json()) == 1
    assert client.post("/api/documents", files={"file": ("x.exe", b"x")}, data={"kind": "notes"}).status_code == 400
