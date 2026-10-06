"use client";

import { useState } from "react";
import { analyzePapers, type Doc, type PaperAnalysis } from "@/lib/api";

export default function PapersPanel({ docs, docIds }: { docs: Doc[]; docIds: string[] }) {
  const [res, setRes] = useState<PaperAnalysis>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const papers = docs.filter((d) => d.kind === "paper");

  async function run() {
    setBusy(true); setError("");
    try {
      const selectedPaperIds = docIds.filter((id) => papers.some((p) => p.id === id));
      setRes(await analyzePapers(selectedPaperIds.length ? selectedPaperIds : null));
    } catch (e) { setError(e instanceof Error ? e.message : "Analysis failed"); }
    finally { setBusy(false); }
  }
  const max = Math.max(1, ...(res?.topics.map((t) => t.count) ?? [1]));

  return (
    <div className="mx-auto h-full max-w-3xl space-y-6 overflow-y-auto px-6 py-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="font-serif text-2xl font-semibold tracking-tight">Past-paper trends</h2>
          <p className="text-sm text-muted">Groups similar questions across your papers, ranks them by how often they repeat, and points to where you studied them.</p>
        </div>
        <button onClick={run} disabled={busy || papers.length === 0} className="h-11 shrink-0 rounded-md bg-accent px-4 text-sm font-medium text-accent-ink disabled:opacity-40">
          {busy ? "Analysing…" : "Analyse papers"}
        </button>
      </div>
      {papers.length === 0 && <p className="text-sm text-muted">Add at least one question paper and choose “Past paper” as its type.</p>}
      {error && <p role="alert" className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      {res && (
        <>
          <p className="text-sm text-muted">{res.questions} questions from {res.papers} {res.papers === 1 ? "paper" : "papers"}.</p>
          {res.topics.length === 0 && <p className="text-sm">No numbered questions were found. Papers need lines starting with “1.”, “Q1” or “(a)”.</p>}
          <ol className="space-y-3">
            {res.topics.map((t, i) => (
              <li key={i} className="rounded-md border border-line bg-surface p-4">
                <div className="flex items-baseline justify-between gap-3">
                  <p className="font-serif text-lg leading-snug">{t.topic}</p>
                  <span className="shrink-0 text-sm font-medium">{t.count}× · {t.weightage}%</span>
                </div>
                <div className="mt-2 h-1.5 rounded-full bg-line" role="img" aria-label={`Asked ${t.count} times`}>
                  <div className="h-full rounded-full bg-accent" style={{ width: `${(t.count / max) * 100}%` }} />
                </div>
                <p className="mt-2 text-xs text-muted">In {t.papers.join(", ")}</p>
                {t.study.length > 0 && (
                  <p className="mt-2 text-sm"><span className="cite">Study</span>{" "}
                    {t.study.map((s) => `${s.source}${s.page ? ` p.${s.page}` : ""}${s.section ? ` — ${s.section}` : ""}`).join("; ")}
                  </p>
                )}
              </li>
            ))}
          </ol>
        </>
      )}
    </div>
  );
}
