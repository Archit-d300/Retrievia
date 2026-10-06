export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Kind = "notes" | "textbook" | "paper";
export interface Doc { id: string; name: string; kind: Kind; pages: number; chunks: number; created: number }
export interface Source {
  n: number; label: string; source: string; page: number | null; section: string | null;
  origin: "local" | "web"; url: string | null; score: number | null; snippet: string;
}
export interface Step { node: string; detail: string }
export interface Result { answer: string; sources: Source[]; tokens: number; verdict?: string; mode?: string }
export interface Topic {
  topic: string; count: number; weightage: number; papers: string[]; examples: string[];
  study: { source: string; page: number | null; section: string | null; score: number }[];
}
export interface PaperAnalysis { papers: number; questions: number; topics: Topic[] }
export interface Health { status: string; llm: string; grader: string; embeddings: string; hf_token_set: boolean }

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed (${res.status})`);
  }
  return res.json();
}

export const getHealth = () => fetch(`${API}/api/health`).then(json<Health>);
export const listDocs = () => fetch(`${API}/api/documents`).then(json<Doc[]>);
export const deleteDoc = (id: string) => fetch(`${API}/api/documents/${id}`, { method: "DELETE" }).then(json);
export function uploadDoc(file: File, kind: Kind) {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("kind", kind);
  return fetch(`${API}/api/documents`, { method: "POST", body: fd }).then(json<Doc>);
}
export const analyzePapers = (doc_ids: string[] | null) =>
  fetch(`${API}/api/analyze/papers`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ doc_ids: doc_ids.length ? doc_ids : null }),
  }).then(json<PaperAnalysis>);

/** Streams agent steps as they complete (SSE over fetch), then resolves with the final result. */
export async function streamChat(
  body: { question: string; doc_ids: string[] | null; use_web: boolean; history: { role: string; content: string }[] },
  onStep: (s: Step) => void,
): Promise<Result> {
  const res = await fetch(`${API}/api/chat/stream`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  if (!res.ok || !res.body) throw new Error(`Request failed (${res.status})`);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  let final: Result | null = null;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const events = buf.split("\n\n");
    buf = events.pop() ?? "";
    for (const ev of events) {
      const line = ev.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;
      const msg = JSON.parse(line.slice(6));
      if (msg.type === "step") onStep({ node: msg.node, detail: msg.detail });
      else if (msg.type === "final") final = msg;
      else if (msg.type === "error") throw new Error(msg.message);
    }
  }
  if (!final) throw new Error("The answer stream ended unexpectedly.");
  return final;
}
