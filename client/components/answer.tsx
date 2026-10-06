"use client";

import { Globe, BookOpen, Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Result, Step } from "@/lib/api";
import { cn } from "@/lib/utils";

const NODE_LABEL: Record<string, string> = {
  route: "Understood the request", rewrite: "Clarified the question", retrieve: "Searched your material",
  grade: "Checked the results", web_search: "Looked on the web", generate: "Wrote the answer",
  summarize: "Wrote the summary", analyze: "Compared the papers",
};

export function StepList({ steps, pending }: { steps: Step[]; pending?: boolean }) {
  return (
    <ol className="space-y-1.5 text-sm">
      {steps.map((s, i) => (
        <li key={i} className="flex gap-2">
          <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-accent" />
          <span><span className="font-medium">{NODE_LABEL[s.node] ?? s.node}.</span> <span className="text-muted">{s.detail}</span></span>
        </li>
      ))}
      {pending && (
        <li className="flex items-center gap-2 text-muted"><Loader2 className="size-3.5 animate-spin" /> Working…</li>
      )}
    </ol>
  );
}

const VERDICT: Record<string, string> = {
  correct: "Well covered by your material",
  ambiguous: "Only partly covered by your material",
  incorrect: "Not found in your material",
};

export function AnswerView({ result, steps, pending }: { result?: Result; steps: Step[]; pending?: boolean }) {
  const text = (result?.answer ?? "").replace(/\[(\d+)\]/g, "[$1](#cite-$1)");
  return (
    <div className="space-y-4">
      {pending && !result && <StepList steps={steps} pending />}
      {result && (
        <>
          <div className="answer prose prose-neutral max-w-none dark:prose-invert prose-p:my-2">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                a: ({ href, children }) =>
                  href?.startsWith("#cite-") ? (
                    <sup className="cite" title={result.sources[Number(href.slice(6)) - 1]?.label}>{children}</sup>
                  ) : (
                    <a href={href} target="_blank" rel="noreferrer">{children}</a>
                  ),
              }}
            >
              {text}
            </ReactMarkdown>
          </div>

          {result.sources.length > 0 && (
            <ul className="grid gap-2 sm:grid-cols-2">
              {result.sources.map((s) => (
                <li key={s.n} className="rounded-md border border-line bg-surface p-3 text-sm">
                  <div className="flex items-start gap-2">
                    <span className="cite mt-0.5 shrink-0">{s.n}</span>
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5 font-medium">
                        {s.origin === "web" ? <Globe className="size-3.5 shrink-0 text-web" /> : <BookOpen className="size-3.5 shrink-0 text-accent" />}
                        {s.url ? <a href={s.url} target="_blank" rel="noreferrer" className="truncate underline-offset-2 hover:underline">{s.source}</a> : <span className="truncate">{s.label}</span>}
                      </div>
                      <p className="mt-1 line-clamp-2 text-muted">{s.snippet}</p>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}

          <details className="text-sm text-muted">
            <summary className="cursor-pointer select-none">
              How this was answered
              {result.verdict && <> · {VERDICT[result.verdict] ?? result.verdict}</>}
              {result.sources.some((s) => s.origin === "web") && <> · web sources added</>}
              {" · "}{result.tokens > 0 ? `${result.tokens.toLocaleString()} tokens` : "no model tokens used"}
            </summary>
            <div className={cn("mt-2 rounded-md border border-line bg-surface p-3 text-ink")}><StepList steps={steps} /></div>
          </details>
        </>
      )}
    </div>
  );
}
