"use client";

import { useState } from "react";
import { streamChat, type Result, type Step } from "@/lib/api";
import { AnswerView } from "./answer";
import { cn } from "@/lib/utils";

const STYLES = [
  { id: "revision notes", label: "Revision notes", hint: "Short bullets to skim the night before" },
  { id: "chapter-wise summary", label: "Chapter-wise", hint: "One block per chapter or topic" },
  { id: "exam guide", label: "Exam guide", hint: "Key points plus likely questions" },
];

export default function SummaryPanel({ docIds, hasDocs }: { docIds: string[]; hasDocs: boolean }) {
  const [style, setStyle] = useState(STYLES[0].id);
  const [topic, setTopic] = useState("");
  const [busy, setBusy] = useState(false);
  const [steps, setSteps] = useState<Step[]>([]);
  const [result, setResult] = useState<Result>();

  async function run() {
    setBusy(true); setResult(undefined); setSteps([]);
    const question = `Summarize ${topic.trim() || "my material"} as ${style}`;
    try {
      setResult(await streamChat({ question, doc_ids: docIds.length ? docIds : null, use_web: false, history: [] }, (s) => setSteps((p) => [...p, s])));
    } catch (e) {
      setResult({ answer: `**Couldn't create the summary.** ${e instanceof Error ? e.message : ""}`, sources: [], tokens: 0 });
    } finally { setBusy(false); }
  }

  return (
    <div className="mx-auto h-full max-w-3xl space-y-6 overflow-y-auto px-6 py-6">
      <div>
        <h2 className="font-serif text-2xl font-semibold tracking-tight">Summaries</h2>
        <p className="text-sm text-muted">Pick a format. Leave the topic empty to summarise everything selected, or name a chapter.</p>
      </div>
      <div className="grid gap-2 sm:grid-cols-3">
        {STYLES.map((s) => (
          <button key={s.id} onClick={() => setStyle(s.id)} aria-pressed={style === s.id}
            className={cn("rounded-md border p-3 text-left", style === s.id ? "border-accent bg-accent/10" : "border-line bg-surface hover:border-accent")}>
            <div className="text-sm font-medium">{s.label}</div><div className="text-xs text-muted">{s.hint}</div>
          </button>
        ))}
      </div>
      <div className="flex gap-2">
        <input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Optional: a chapter or topic, e.g. memory management"
          className="h-11 flex-1 rounded-md border border-line bg-surface px-3 text-sm" />
        <button onClick={run} disabled={busy || !hasDocs} className="h-11 rounded-md bg-accent px-4 text-sm font-medium text-accent-ink disabled:opacity-40">
          {busy ? "Summarising…" : "Create summary"}
        </button>
      </div>
      {!hasDocs && <p className="text-sm text-muted">Add notes or a textbook on the left first.</p>}
      {(busy || result) && <AnswerView result={result} steps={steps} pending={busy} />}
    </div>
  );
}
