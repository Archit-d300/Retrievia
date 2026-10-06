"use client";

import { useCallback, useEffect, useState } from "react";
import { getHealth, listDocs, type Doc, type Health } from "@/lib/api";
import { cn } from "@/lib/utils";
import Shelf from "./shelf";
import ChatPanel from "./chat-panel";
import SummaryPanel from "./summary-panel";
import PapersPanel from "./papers-panel";

const TABS = [{ id: "ask", label: "Ask" }, { id: "summaries", label: "Summaries" }, { id: "papers", label: "Past papers" }] as const;

export default function Workspace() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [tab, setTab] = useState<(typeof TABS)[number]["id"]>("ask");
  const [health, setHealth] = useState<Health | "offline" | null>(null);

  const refresh = useCallback(async () => {
    try {
      const d = await listDocs();
      setDocs(d);
      setSelected((s) => new Set([...s].filter((id) => d.some((x) => x.id === id))));
    } catch { setHealth("offline"); }
  }, []);

  useEffect(() => {
    refresh();
    getHealth().then(setHealth).catch(() => setHealth("offline"));
  }, [refresh]);

  const ids = [...selected];
  const toggle = (id: string) => setSelected((s) => { const n = new Set(s); if (n.has(id)) n.delete(id); else n.add(id); return n; });

  return (
    <div className="grid h-full grid-rows-[auto_1fr] md:grid-cols-[300px_1fr] md:grid-rows-1">
      <div className="max-h-[45vh] md:max-h-none md:h-full"><Shelf docs={docs} selected={selected} onToggle={toggle} onChange={refresh} /></div>
      <main className="flex min-h-0 flex-col">
        {health === "offline" && (
          <div role="alert" className="border-b border-line bg-mark px-6 py-2 text-sm text-mark-ink">
            Can’t reach the API. Start it with <code>uvicorn app.main:app --reload</code> in <code>backend/</code>.
          </div>
        )}
        {health && health !== "offline" && !health.hf_token_set && (
          <div role="status" className="border-b border-line bg-mark px-6 py-2 text-sm text-mark-ink">
            No Hugging Face token set. Add <code>HF_TOKEN</code> to <code>backend/.env</code> so answers can be generated.
          </div>
        )}
        <nav className="flex gap-1 border-b border-line bg-surface px-4" aria-label="Sections">
          {TABS.map((t) => (
            <button key={t.id} onClick={() => setTab(t.id)} aria-current={tab === t.id}
              className={cn("border-b-2 px-3 py-3 text-sm font-medium", tab === t.id ? "border-accent text-ink" : "border-transparent text-muted hover:text-ink")}>
              {t.label}
            </button>
          ))}
          {health && health !== "offline" && <span className="ml-auto self-center text-xs text-muted">{health.llm.split("/")[1]}</span>}
        </nav>
        <div className="min-h-0 flex-1">
          {tab === "ask" && <ChatPanel docIds={ids} />}
          {tab === "summaries" && <SummaryPanel docIds={ids} hasDocs={docs.some((d) => d.kind !== "paper")} />}
          {tab === "papers" && <PapersPanel docs={docs} docIds={ids} />}
        </div>
      </main>
    </div>
  );
}
