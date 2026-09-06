"use client";

import { Check, Copy, Loader2, Play } from "lucide-react";
import { useState } from "react";

import type { Endpoint } from "@/lib/docs/endpoints";
import { cn } from "@/lib/utils";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";

interface Result {
  status: number;
  ms: number;
  body: string;
  ok: boolean;
}

/** Fills `:name` segments and appends whatever query values were typed. */
function buildUrl(endpoint: Endpoint, path: Record<string, string>, query: Record<string, string>) {
  let url = endpoint.path;
  for (const [key, value] of Object.entries(path)) {
    url = url.replace(`:${key}`, encodeURIComponent(value || `:${key}`));
  }
  const search = new URLSearchParams(
    Object.entries(query).filter(([, v]) => v.trim() !== "")
  ).toString();
  return `${API_URL}${url}${search ? `?${search}` : ""}`;
}

export function Playground({
  endpoint,
  apiKey,
}: {
  endpoint: Endpoint;
  apiKey: string;
}) {
  const [pathValues, setPathValues] = useState<Record<string, string>>(() =>
    Object.fromEntries((endpoint.pathParams ?? []).map((p) => [p.name, p.example ?? ""]))
  );
  const [queryValues, setQueryValues] = useState<Record<string, string>>(() =>
    Object.fromEntries((endpoint.query ?? []).map((p) => [p.name, p.example ?? ""]))
  );
  const [body, setBody] = useState(() =>
    endpoint.body ? JSON.stringify(endpoint.body, null, 2) : ""
  );
  const [result, setResult] = useState<Result | null>(null);
  const [sending, setSending] = useState(false);
  const [copied, setCopied] = useState(false);

  const url = buildUrl(endpoint, pathValues, queryValues);
  const hasBody = endpoint.method !== "GET" && Boolean(endpoint.body);

  async function send() {
    setSending(true);
    setResult(null);
    const started = performance.now();
    try {
      const res = await fetch(url, {
        method: endpoint.method,
        headers: {
          Authorization: `Bearer ${apiKey}`,
          ...(hasBody ? { "Content-Type": "application/json" } : {}),
        },
        body: hasBody ? body : undefined,
      });
      const text = await res.text();
      let pretty = text;
      try {
        pretty = JSON.stringify(JSON.parse(text), null, 2);
      } catch {
        // Not JSON — show whatever came back rather than swallowing it.
      }
      setResult({
        status: res.status,
        ms: Math.round(performance.now() - started),
        body: pretty,
        ok: res.ok,
      });
    } catch (err) {
      // A network-level failure here is almost always CORS or a wrong base
      // URL, and saying so saves a long detour through the console.
      setResult({
        status: 0,
        ms: Math.round(performance.now() - started),
        ok: false,
        body:
          `Request never reached the API.\n\n${err instanceof Error ? err.message : String(err)}\n\n` +
          `Base URL: ${API_URL}\n` +
          `Usually this is CORS (the API's FRONTEND_ORIGIN must allow this page's origin) ` +
          `or the API not running.`,
      });
    } finally {
      setSending(false);
    }
  }

  function copyCurl() {
    const parts = [`curl -X ${endpoint.method} '${url}'`, `  -H 'Authorization: Bearer ${apiKey || "<your-key>"}'`];
    if (hasBody) {
      parts.push(`  -H 'Content-Type: application/json'`);
      parts.push(`  -d '${body.replace(/\n\s*/g, "")}'`);
    }
    navigator.clipboard.writeText(parts.join(" \\\n"));
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }

  return (
    <div className="mt-5 overflow-hidden rounded-xl border border-border/70">
      <div className="flex items-center justify-between gap-3 border-b border-border/60 bg-muted/40 px-3.5 py-2">
        <span className="text-[11px] font-medium text-muted-foreground">Try it</span>
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={copyCurl}
            className="flex items-center gap-1.5 rounded-md border border-border/70 px-2 py-1 text-[11px] text-muted-foreground transition-colors hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
          >
            {copied ? <Check className="size-3" /> : <Copy className="size-3" />}
            {copied ? "Copied" : "cURL"}
          </button>
          <button
            type="button"
            onClick={send}
            disabled={sending || !apiKey}
            title={apiKey ? undefined : "Paste an API key above first"}
            className="flex items-center gap-1.5 rounded-md bg-primary px-2.5 py-1 text-[11px] font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
          >
            {sending ? <Loader2 className="size-3 animate-spin" /> : <Play className="size-3" />}
            Send
          </button>
        </div>
      </div>

      <div className="space-y-3 p-3.5">
        {endpoint.pathParams && endpoint.pathParams.length > 0 && (
          <Fields
            legend="Path"
            params={endpoint.pathParams}
            values={pathValues}
            onChange={(n, v) => setPathValues((s) => ({ ...s, [n]: v }))}
          />
        )}

        {endpoint.query && endpoint.query.length > 0 && (
          <Fields
            legend="Query"
            params={endpoint.query}
            values={queryValues}
            onChange={(n, v) => setQueryValues((s) => ({ ...s, [n]: v }))}
          />
        )}

        {hasBody && (
          <label className="block">
            <span className="mb-1.5 block text-[11px] font-medium text-muted-foreground">
              Body — edit freely
            </span>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              spellCheck={false}
              rows={Math.min(14, body.split("\n").length + 1)}
              className="w-full rounded-lg border border-border/70 bg-muted/30 p-2.5 font-mono text-[11px] leading-relaxed outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20"
            />
          </label>
        )}

        <p className="truncate font-mono text-[10px] text-muted-foreground" title={url}>
          {endpoint.method} {url}
        </p>

        {result && (
          <div>
            <div className="mb-1.5 flex items-center gap-2 text-[11px]">
              <span
                className={cn(
                  "rounded px-1.5 py-0.5 font-mono font-medium",
                  result.ok
                    ? "bg-[color-mix(in_oklch,var(--agent-2),transparent_85%)] text-[var(--agent-2)]"
                    : "bg-destructive/10 text-destructive"
                )}
              >
                {result.status || "network error"}
              </span>
              <span className="tabular-nums text-muted-foreground">{result.ms} ms</span>
            </div>
            <pre className="scrollbar-thin max-h-72 overflow-auto rounded-lg border border-border/70 bg-muted/30 p-2.5 font-mono text-[11px] leading-relaxed">
              {result.body}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

function Fields({
  legend,
  params,
  values,
  onChange,
}: {
  legend: string;
  params: { name: string; type: string; required?: boolean }[];
  values: Record<string, string>;
  onChange: (name: string, value: string) => void;
}) {
  return (
    <fieldset>
      <legend className="mb-1.5 text-[11px] font-medium text-muted-foreground">{legend}</legend>
      <div className="grid gap-2 sm:grid-cols-2">
        {params.map((p) => (
          <label key={p.name} className="flex items-center gap-2">
            <span className="w-24 shrink-0 truncate font-mono text-[11px] text-muted-foreground">
              {p.name}
              {p.required && <span className="text-destructive">*</span>}
            </span>
            <input
              value={values[p.name] ?? ""}
              onChange={(e) => onChange(p.name, e.target.value)}
              placeholder={p.type}
              spellCheck={false}
              className="min-w-0 flex-1 rounded-md border border-border/70 bg-muted/30 px-2 py-1 font-mono text-[11px] outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20"
            />
          </label>
        ))}
      </div>
    </fieldset>
  );
}
