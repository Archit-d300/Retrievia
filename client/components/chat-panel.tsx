"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowUp, Globe } from "lucide-react";
import { streamChat, type Result, type Step } from "@/lib/api";
import { AnswerView } from "./answer";
import { cn } from "@/lib/utils";

interface Msg { role: "user" | "assistant"; content: string; result?: Result; steps?: Step[]; pending?: boolean }

const EXAMPLES = [
  "Explain deadlock prevention.",
  "Where is Dijkstra's algorithm discussed in my notes?",
  "Which topics are repeatedly asked in previous-year papers?",
];

export default function ChatPanel({ docIds }: { docIds: string[] }) {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [q, setQ] = useState("");
  const [web, setWeb] = useState(true);
  const [busy, setBusy] = useState(false);
  const end = useRef<HTMLDivElement>(null);
useEffect(() => {
  end.current?.scrollIntoView({
    behavior: "smooth",
    block: "end",
  });
}, [msgs]);

  async function ask(question: string) {
    if (!question.trim() || busy) return;
    const history = msgs.filter((m) => !m.pending).map((m) => ({ role: m.role, content: m.content }));
    setMsgs((m) => [...m, { role: "user", content: question }, { role: "assistant", content: "", steps: [], pending: true }]);
    setQ(""); setBusy(true);
    const patch = (fn: (m: Msg) => Msg) => setMsgs((all) => all.map((m, i) => (i === all.length - 1 ? fn(m) : m)));
    try {
      const result = await streamChat(
        { question, doc_ids: docIds.length ? docIds : null, use_web: web, history },
        (s) => patch((m) => ({ ...m, steps: [...(m.steps ?? []), s] })),
      );
      patch((m) => ({ ...m, content: result.answer, result, pending: false }));
    } catch (e) {
      const err = e instanceof Error ? e.message : "Something went wrong";
      patch((m) => ({ ...m, pending: false, result: { answer: `**Couldn't get an answer.** ${err}\n\nCheck that the API is running and your Hugging Face token is set.`, sources: [], tokens: 0 } }));
    } finally { setBusy(false); }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 space-y-8 overflow-y-auto px-6 py-6">
        {msgs.length === 0 ? (
          <div className="mx-auto mt-10 max-w-xl">
            <h2 className="font-serif text-3xl font-semibold tracking-tight">What are you revising today?</h2>
            <p className="mt-2 text-muted">Answers come from your uploaded material first. Every claim carries a highlighted number that points to its page.</p>
            <div className="mt-6 flex flex-col items-start gap-2">
              {EXAMPLES.map((e) => (
                <button key={e} onClick={() => ask(e)} className="rounded-md border border-line bg-surface px-3 py-2 text-left text-sm hover:border-accent">{e}</button>
              ))}
            </div>
          </div>
        ) : (
          msgs.map((m, i) => m.role === "user" ? (
            <div key={i} className="ml-auto max-w-[80%] rounded-lg bg-accent px-4 py-2.5 text-accent-ink">{m.content}</div>
          ) : (
            <div key={i} className="max-w-3xl"><AnswerView result={m.result} steps={m.steps ?? []} pending={m.pending} /></div>
          ))
        )}
        <div ref={end} />
      </div>

      <form onSubmit={(e) => { e.preventDefault(); ask(q); }} className="border-t border-line bg-surface p-4">
        <div className="mx-auto flex max-w-3xl items-end gap-2">
          <textarea value={q} onChange={(e) => setQ(e.target.value)} rows={1} placeholder="Ask about your notes, textbook or past papers"
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(q); } }}
            className="max-h-32 min-h-11 flex-1 resize-none rounded-md border border-line bg-paper px-3 py-2.5 text-sm" />
          <button type="button" aria-pressed={web} onClick={() => setWeb(!web)} title="Fall back to trusted educational sites when your material doesn't cover a question"
            className={cn("flex h-11 items-center gap-1.5 rounded-md border px-3 text-sm", web ? "border-web text-web" : "border-line text-muted")}>
            <Globe className="size-4" /> Web {web ? "on" : "off"}
          </button>
          <button disabled={busy || !q.trim()} aria-label="Send" className="grid size-11 place-items-center rounded-md bg-accent text-accent-ink disabled:opacity-40">
            <ArrowUp className="size-5" />
          </button>
        </div>
      </form>
    </div>
  );
}
