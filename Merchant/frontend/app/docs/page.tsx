"use client";

import { ArrowLeft, Eye, EyeOff, KeyRound } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Logo } from "@/components/brand/logo";
import { CodeBlock } from "@/components/docs/code-block";
import { Playground } from "@/components/docs/playground";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { Button } from "@/components/ui/button";
import { ENDPOINTS, ERRORS, SCOPES, type Endpoint } from "@/lib/docs/endpoints";
import { cn } from "@/lib/utils";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";
const KEY_STORAGE = "agentic-docs-key";

const METHOD_TONE: Record<string, string> = {
  GET: "text-[var(--agent-2)] border-[color-mix(in_oklch,var(--agent-2),transparent_60%)]",
  POST: "text-[var(--agent-1)] border-[color-mix(in_oklch,var(--agent-1),transparent_60%)]",
  DELETE: "text-destructive border-destructive/40",
};

export default function DocsPage() {
  // Session storage, not local: a key pasted to try an endpoint shouldn't
  // outlive the tab it was pasted into.
  const [apiKey, setApiKey] = useState(() => {
    if (typeof window === "undefined") return "";
    return window.sessionStorage.getItem(KEY_STORAGE) ?? "";
  });
  const [revealed, setRevealed] = useState(false);

  function updateKey(value: string) {
    setApiKey(value);
    try {
      window.sessionStorage.setItem(KEY_STORAGE, value);
    } catch {
      // Private mode blocks storage; the key still works for this render.
    }
  }

  return (
    <div className="flex flex-1 flex-col">
      <header className="sticky top-0 z-40 border-b border-border/60 bg-background/70 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3">
          <Logo markClassName="size-7" textClassName="text-[15px]" />
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Button variant="ghost" size="sm" render={<Link href="/" />}>
              <ArrowLeft className="size-4" /> Back home
            </Button>
          </div>
        </div>
      </header>

      <div className="mx-auto grid w-full max-w-6xl flex-1 gap-10 px-6 py-10 lg:grid-cols-[210px_1fr]">
        <nav className="hidden lg:block">
          <div className="scrollbar-thin sticky top-24 max-h-[calc(100dvh-8rem)] space-y-0.5 overflow-y-auto pr-2 text-sm">
            <SideLink id="overview">Overview</SideLink>
            <SideLink id="auth">Authentication</SideLink>
            <SideLink id="scopes">Scopes</SideLink>
            <p className="px-3 pt-4 pb-1 text-[11px] font-medium text-muted-foreground/70">
              Endpoints
            </p>
            {ENDPOINTS.map((e) => (
              <SideLink key={e.id} id={e.id}>
                {e.title}
              </SideLink>
            ))}
            <p className="px-3 pt-4 pb-1 text-[11px] font-medium text-muted-foreground/70">
              Reference
            </p>
            <SideLink id="lifecycle">Order lifecycle</SideLink>
            <SideLink id="money">Money and stock</SideLink>
            <SideLink id="errors">Errors</SideLink>
          </div>
        </nav>

        <main className="min-w-0 space-y-14">
          <section id="overview" className="scroll-mt-24">
            <h1 className="font-display text-3xl font-semibold text-balance sm:text-4xl">
              Agent API
            </h1>
            <p className="mt-4 max-w-[62ch] leading-relaxed text-muted-foreground">
              One HTTP API that lets an authorized shopping agent read this catalog, hold
              stock while a buyer decides, and register the order it collected payment
              for. It is the whole surface — there is no other way in, and the agent
              never touches this database directly.
            </p>
            <div className="mt-5 rounded-xl border border-border/70 bg-muted/30 p-4">
              <p className="text-[11px] font-medium text-muted-foreground">Base URL</p>
              <p className="mt-1 font-mono text-sm break-all">{API_URL}</p>
            </div>
          </section>

          <section id="auth" className="scroll-mt-24">
            <h2 className="font-display text-2xl font-semibold">Authentication</h2>
            <p className="mt-3 max-w-[62ch] leading-relaxed text-muted-foreground">
              Every agent endpoint takes a bearer token. Keys are issued from the admin
              console, shown once, and stored only as a hash — if you lose one, issue
              another.
            </p>
            <CodeBlock className="mt-4">{`Authorization: Bearer ac_test_…`}</CodeBlock>

            <div className="mt-5 rounded-xl border border-border/70 p-4">
              <div className="flex items-center gap-2">
                <KeyRound className="size-4 text-muted-foreground" />
                <p className="text-sm font-medium">Your key, for the examples below</p>
              </div>
              <p className="mt-1.5 text-[13px] leading-relaxed text-muted-foreground">
                Paste a key and every <span className="font-medium text-foreground">Send</span>{" "}
                button on this page calls the real API with it. It is kept in this tab&apos;s
                session storage only — closing the tab forgets it, and it is never sent
                anywhere except the base URL above.
              </p>
              <div className="mt-3 flex gap-2">
                <input
                  type={revealed ? "text" : "password"}
                  value={apiKey}
                  onChange={(e) => updateKey(e.target.value)}
                  placeholder="ac_test_…"
                  spellCheck={false}
                  autoComplete="off"
                  className="min-w-0 flex-1 rounded-lg border border-border/70 bg-muted/30 px-3 py-2 font-mono text-sm outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20"
                />
                <button
                  type="button"
                  onClick={() => setRevealed((v) => !v)}
                  aria-label={revealed ? "Hide the key" : "Show the key"}
                  className="grid size-10 shrink-0 place-items-center rounded-lg border border-border/70 text-muted-foreground transition-colors hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
                >
                  {revealed ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              </div>
            </div>
          </section>

          <section id="scopes" className="scroll-mt-24">
            <h2 className="font-display text-2xl font-semibold">Scopes</h2>
            <p className="mt-3 max-w-[62ch] leading-relaxed text-muted-foreground">
              A key carries scopes, and each endpoint names the one it needs. Reading and
              writing are separate on purpose: a key that only shops cannot place an
              order.
            </p>
            <dl className="mt-4 divide-y divide-border/60 overflow-hidden rounded-xl border border-border/70">
              {SCOPES.map((s) => (
                <div key={s.name} className="grid gap-1 p-4 sm:grid-cols-[11rem_1fr] sm:gap-4">
                  <dt className="font-mono text-[13px]">{s.name}</dt>
                  <dd className="text-[13px] leading-relaxed text-muted-foreground">
                    {s.description}
                  </dd>
                </div>
              ))}
            </dl>
          </section>

          {ENDPOINTS.map((endpoint) => (
            <EndpointSection key={endpoint.id} endpoint={endpoint} apiKey={apiKey} />
          ))}

          <section id="lifecycle" className="scroll-mt-24">
            <h2 className="font-display text-2xl font-semibold">Order lifecycle</h2>
            <p className="mt-3 max-w-[62ch] leading-relaxed text-muted-foreground">
              The order the endpoints above are meant to be called in. Steps 2 and 5 are
              the ones people skip, and both cost real money when they go wrong.
            </p>
            <ol className="mt-5 space-y-3">
              {[
                ["Read the shelves", "GET /catalog/facets — so you constrain by values that exist."],
                ["Find the product", "GET /catalog/search — category and brand as constraints, q for adjectives."],
                ["Hold the stock", "POST /reservations — before the buyer starts paying, not after."],
                ["Take the payment", "Your side. This API never sees a card and has no endpoint that charges one."],
                ["Register the order", "POST /orders — idempotent, so retry a timeout freely."],
                ["Follow it", "GET /orders/:id — until DELIVERED, or POST /orders/:id/cancel while you still can."],
              ].map(([title, detail], i) => (
                <li key={title} className="flex gap-3.5">
                  <span className="mt-0.5 grid size-6 shrink-0 place-items-center rounded-md bg-[color-mix(in_oklch,var(--agent-1),transparent_88%)] font-mono text-[11px] text-[var(--agent-1)]">
                    {i + 1}
                  </span>
                  <div>
                    <p className="text-[15px] font-medium">{title}</p>
                    <p className="mt-0.5 text-[13px] leading-relaxed text-muted-foreground">
                      {detail}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </section>

          <section id="money" className="scroll-mt-24">
            <h2 className="font-display text-2xl font-semibold">Money and stock</h2>
            <div className="mt-4 space-y-4 text-[15px] leading-relaxed text-muted-foreground">
              <p>
                <span className="font-medium text-foreground">Prices are integers</span> in
                the smallest currency unit. ₹4,099.00 is <code className="font-mono text-[13px]">409900</code>.
                Never send a float.
              </p>
              <p>
                <span className="font-medium text-foreground">Three stock numbers,</span>{" "}
                and they differ. <code className="font-mono text-[13px]">stock_on_hand</code> is
                what is physically there.{" "}
                <code className="font-mono text-[13px]">stock_held</code> is what other
                checkouts are holding.{" "}
                <code className="font-mono text-[13px]">stock_quantity</code> is on_hand
                minus held — the only one you should promise a buyer.
              </p>
              <p>
                <span className="font-medium text-foreground">This API never charges anyone.</span>{" "}
                It records an order you have already been paid for. If registering fails
                with <code className="font-mono text-[13px]">INSUFFICIENT_STOCK</code>, the
                goods went while your buyer was paying — refund them, because that call
                will never succeed.
              </p>
            </div>
          </section>

          <section id="errors" className="scroll-mt-24">
            <h2 className="font-display text-2xl font-semibold">Errors</h2>
            <p className="mt-3 max-w-[62ch] leading-relaxed text-muted-foreground">
              Every failure comes back in the same shape, with a stable{" "}
              <code className="font-mono text-[13px]">code</code> worth branching on and a
              message safe to show a person.
            </p>
            <CodeBlock className="mt-4">{`{
  "success": false,
  "error": { "code": "INSUFFICIENT_STOCK", "message": "Only 2 left of 'Vivo X21' — 3 isn't available right now." }
}`}</CodeBlock>
            <div className="mt-5 overflow-hidden rounded-xl border border-border/70">
              <table className="w-full text-left text-[13px]">
                <thead className="border-b border-border/60 bg-muted/40 text-[11px] text-muted-foreground">
                  <tr>
                    <th className="px-4 py-2 font-medium">Status</th>
                    <th className="px-4 py-2 font-medium">Code</th>
                    <th className="px-4 py-2 font-medium">Meaning</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {ERRORS.map((e) => (
                    <tr key={e.code}>
                      <td className="px-4 py-2 font-mono tabular-nums">{e.status}</td>
                      <td className="px-4 py-2 font-mono">{e.code}</td>
                      <td className="px-4 py-2 text-muted-foreground">{e.meaning}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}

function SideLink({ id, children }: { id: string; children: React.ReactNode }) {
  return (
    <a
      href={`#${id}`}
      className="block truncate rounded-md px-3 py-1.5 text-muted-foreground transition-colors hover:bg-foreground/[0.04] hover:text-foreground"
    >
      {children}
    </a>
  );
}

function EndpointSection({ endpoint, apiKey }: { endpoint: Endpoint; apiKey: string }) {
  return (
    <section id={endpoint.id} className="scroll-mt-24">
      <div className="flex flex-wrap items-center gap-2.5">
        <span
          className={cn(
            "rounded border px-1.5 py-0.5 font-mono text-[11px] font-medium",
            METHOD_TONE[endpoint.method]
          )}
        >
          {endpoint.method}
        </span>
        <code className="font-mono text-[13px] break-all">{endpoint.path}</code>
        <span className="rounded border border-border/70 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
          {endpoint.scope}
        </span>
      </div>

      <h2 className="font-display mt-3 text-2xl font-semibold">{endpoint.title}</h2>
      <p className="mt-2 max-w-[62ch] leading-relaxed text-muted-foreground">
        {endpoint.summary}
      </p>

      {endpoint.notes && (
        <ul className="mt-4 space-y-2">
          {endpoint.notes.map((note) => (
            <li key={note} className="flex gap-2.5 text-[13px] leading-relaxed text-muted-foreground">
              <span
                aria-hidden="true"
                className="mt-[0.55rem] size-1 shrink-0 rounded-full bg-[var(--agent-1)]"
              />
              <span dangerouslySetInnerHTML={{ __html: inlineCode(note) }} />
            </li>
          ))}
        </ul>
      )}

      {(endpoint.pathParams || endpoint.query || endpoint.bodyFields) && (
        <ParamTable endpoint={endpoint} />
      )}

      <Playground endpoint={endpoint} apiKey={apiKey} />

      <details className="mt-3 group">
        <summary className="cursor-pointer text-[13px] text-muted-foreground transition-colors hover:text-foreground">
          Example response
        </summary>
        <CodeBlock className="mt-2">{endpoint.response}</CodeBlock>
      </details>
    </section>
  );
}

function ParamTable({ endpoint }: { endpoint: Endpoint }) {
  const groups = [
    { label: "Path", params: endpoint.pathParams },
    { label: "Query", params: endpoint.query },
    { label: "Body", params: endpoint.bodyFields },
  ].filter((g) => g.params && g.params.length > 0);

  return (
    <div className="mt-5 space-y-4">
      {groups.map((group) => (
        <div key={group.label} className="overflow-hidden rounded-xl border border-border/70">
          <p className="border-b border-border/60 bg-muted/40 px-4 py-1.5 text-[11px] font-medium text-muted-foreground">
            {group.label}
          </p>
          <table className="w-full text-left text-[13px]">
            <tbody className="divide-y divide-border/60">
              {group.params!.map((p) => (
                <tr key={p.name}>
                  <td className="w-48 px-4 py-2 align-top font-mono text-[12px]">
                    {p.name}
                    {p.required && <span className="text-destructive">*</span>}
                  </td>
                  <td className="w-20 px-2 py-2 align-top font-mono text-[11px] text-muted-foreground">
                    {p.type}
                  </td>
                  <td className="px-4 py-2 text-muted-foreground">{p.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}

/** Backticks in the notes above become code. The source is this file, not
 *  user input, so there is nothing to sanitise. */
function inlineCode(text: string) {
  return text.replace(
    /`([^`]+)`/g,
    '<code class="font-mono text-[12px] text-foreground">$1</code>'
  );
}
