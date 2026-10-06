"use client";

import { useRef, useState } from "react";
import { FileText, Trash2, Upload } from "lucide-react";
import { deleteDoc, uploadDoc, type Doc, type Kind } from "@/lib/api";
import { cn } from "@/lib/utils";

const KINDS: { id: Kind; label: string }[] = [
  { id: "notes", label: "Notes" }, { id: "textbook", label: "Textbook" }, { id: "paper", label: "Past paper" },
];

export default function Shelf({ docs, selected, onToggle, onChange }: {
  docs: Doc[]; selected: Set<string>; onToggle: (id: string) => void; onChange: () => void;
}) {
  const [kind, setKind] = useState<Kind>("notes");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [drag, setDrag] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  async function upload(files: FileList | File[]) {
    setBusy(true); setError("");
    try {
      for (const f of Array.from(files)) await uploadDoc(f, kind);
      onChange();
    } catch (e) { setError(e instanceof Error ? e.message : "Upload failed"); }
    finally { setBusy(false); }
  }

  return (
    <aside className="flex h-full flex-col gap-4 border-r border-line bg-surface p-4">
      <div>
        <h1 className="font-serif text-2xl font-semibold tracking-tight">Retrievia</h1>
        <p className="text-sm text-muted">Study from your own material.</p>
      </div>

      <div className="space-y-2">
        <div role="radiogroup" aria-label="Document type" className="grid grid-cols-3 rounded-md border border-line p-0.5 text-xs">
          {KINDS.map((k) => (
            <button key={k.id} role="radio" aria-checked={kind === k.id} onClick={() => setKind(k.id)}
              className={cn("rounded px-2 py-1.5 font-medium transition-colors", kind === k.id ? "bg-accent text-accent-ink" : "text-muted hover:text-ink")}>
              {k.label}
            </button>
          ))}
        </div>
        <button
          onClick={() => input.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); upload(e.dataTransfer.files); }}
          disabled={busy}
          className={cn("flex w-full flex-col items-center gap-1 rounded-md border border-dashed p-4 text-sm transition-colors",
            drag ? "border-accent bg-accent/10" : "border-line hover:border-accent")}>
          <Upload className="size-5 text-accent" />
          <span className="font-medium">{busy ? "Reading and indexing…" : "Add PDF, TXT or MD"}</span>
          <span className="text-xs text-muted">Saved as {KINDS.find((k) => k.id === kind)?.label.toLowerCase()}</span>
        </button>
        <input ref={input} type="file" multiple accept=".pdf,.txt,.md" className="hidden"
          onChange={(e) => { if (e.target.files?.length) upload(e.target.files); e.target.value = ""; }} />
        {error && <p role="alert" className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {docs.length === 0 ? (
          <p className="text-sm text-muted">Nothing here yet. Add your notes or a textbook to start asking questions.</p>
        ) : (
          <>
            <p className="mb-2 text-xs text-muted">
              {selected.size ? `Using ${selected.size} selected` : `Using all ${docs.length}`} — tick to narrow down.
            </p>
            <ul className="space-y-1">
              {docs.map((d) => (
                <li key={d.id} className="group flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-paper">
                  <input type="checkbox" checked={selected.has(d.id)} onChange={() => onToggle(d.id)} aria-label={`Use ${d.name}`} className="accent-[var(--accent)]" />
                  <FileText className="size-4 shrink-0 text-muted" />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm" title={d.name}>{d.name}</div>
                    <div className="text-xs text-muted">{KINDS.find((k) => k.id === d.kind)?.label} · {d.pages} {d.pages === 1 ? "page" : "pages"}</div>
                  </div>
                  <button aria-label={`Delete ${d.name}`} onClick={async () => { await deleteDoc(d.id); onChange(); }}
                    className="rounded p-1 text-muted opacity-0 transition-opacity hover:text-red-600 focus:opacity-100 group-hover:opacity-100">
                    <Trash2 className="size-4" />
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </aside>
  );
}
