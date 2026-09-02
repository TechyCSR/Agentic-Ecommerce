import { ArrowLeft, KeyRound } from "lucide-react";
import Link from "next/link";

import { CodeBlock } from "@/components/docs/code-block";
import { Logo } from "@/components/brand/logo";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
} from "@/components/ui/card";

const sections = [
  { id: "overview", label: "Overview" },
  { id: "authentication", label: "Authentication" },
  { id: "scopes", label: "Scopes" },
  { id: "search", label: "Search catalog" },
  { id: "product", label: "Get a product" },
  { id: "format", label: "Agent-readable format" },
  { id: "errors", label: "Errors" },
];

const searchParams = [
  { name: "q", type: "string", description: "Free-text search across name, description, brand." },
  { name: "category", type: "string", description: "Category name or slug (partial match)." },
  { name: "merchant_id", type: "uuid", description: "Restrict results to one merchant." },
  { name: "store_id", type: "uuid", description: "Restrict results to one store." },
  { name: "brand", type: "string", description: "Partial match on brand." },
  { name: "min_price", type: "integer", description: "Minimum price, in the smallest currency unit." },
  { name: "max_price", type: "integer", description: "Maximum price, in the smallest currency unit." },
  { name: "currency", type: "string", description: "3-letter currency code, e.g. INR." },
  { name: "in_stock", type: "boolean", description: "true to only return variants with stock > 0." },
  { name: "limit", type: "integer", description: "Page size. Default 20, max 100." },
  { name: "offset", type: "integer", description: "Pagination offset. Default 0." },
];

const errorCodes = [
  { status: "401", code: "UNAUTHORIZED", meaning: "Missing or invalid API key." },
  { status: "403", code: "INSUFFICIENT_SCOPE", meaning: "The key doesn't have the scope this endpoint requires." },
  { status: "403", code: "API_KEY_INACTIVE", meaning: "The key exists but has been revoked or suspended." },
  { status: "404", code: "PRODUCT_NOT_FOUND", meaning: "No active, agent-searchable product with that ID." },
  { status: "422", code: "VALIDATION_ERROR", meaning: "A request parameter failed validation." },
];

export default function DocsPage() {
  return (
    <div className="flex flex-1 flex-col">
      <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur supports-backdrop-filter:bg-background/60">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Logo />
          <Button variant="ghost" render={<Link href="/" />}>
            <ArrowLeft className="size-4" /> Back home
          </Button>
        </div>
      </header>

      <div className="mx-auto grid w-full max-w-6xl flex-1 gap-8 px-6 py-10 lg:grid-cols-[200px_1fr]">
        <nav className="hidden lg:block">
          <div className="sticky top-24 space-y-1 text-sm">
            {sections.map((s) => (
              <a
                key={s.id}
                href={`#${s.id}`}
                className="block rounded-md px-3 py-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              >
                {s.label}
              </a>
            ))}
          </div>
        </nav>

        <main className="min-w-0 space-y-14">
          <section id="overview" className="scroll-mt-24 space-y-4">
            <div className="inline-flex items-center gap-2 rounded-full border bg-muted/50 px-3 py-1 text-xs font-medium text-muted-foreground">
              <KeyRound className="size-3 text-indigo-500" />
              Agent &amp; Partner API
            </div>
            <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Agent API Reference
            </h1>
            <p className="max-w-2xl text-lg text-muted-foreground">
              A read-only, versioned API that lets authorized AI shopping
              agents and partners search the catalog and fetch individual
              products in a fixed, standardized format.
            </p>
            <Card>
              <CardContent className="grid gap-4 pt-6 sm:grid-cols-2">
                <div>
                  <p className="text-sm font-medium">Base path</p>
                  <p className="mt-1 font-mono text-sm text-muted-foreground">
                    /api/v1/agent
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium">Access</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    One central API key per agent, issued by the platform
                    operator — see Authentication below.
                  </p>
                </div>
              </CardContent>
            </Card>
          </section>

          <section id="authentication" className="scroll-mt-24 space-y-4">
            <h2 className="text-2xl font-semibold tracking-tight">
              Authentication
            </h2>
            <p className="text-muted-foreground">
              Every request must include an API key as a bearer token. Keys
              are platform-wide: a single key can read across every
              merchant&apos;s agent-searchable catalog, so agents don&apos;t
              need a separate key per store.
            </p>
            <CodeBlock>{`Authorization: Bearer ac_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`}</CodeBlock>
            <p className="text-sm text-muted-foreground">
              Keys are no longer self-service from a merchant dashboard —
              they&apos;re issued by the platform operator from{" "}
              <code className="rounded bg-muted px-1 py-0.5">/admin</code>.
              Contact the platform operator to request a key for your agent
              or integration.
            </p>
          </section>

          <section id="scopes" className="scroll-mt-24 space-y-4">
            <h2 className="text-2xl font-semibold tracking-tight">Scopes</h2>
            <p className="text-muted-foreground">
              Each key is issued with one or more scopes. A request fails
              with <code className="rounded bg-muted px-1 py-0.5">403 INSUFFICIENT_SCOPE</code>{" "}
              if the key doesn&apos;t carry the scope an endpoint requires.
            </p>
            <div className="flex flex-wrap gap-3">
              <Card className="flex-1 basis-56">
                <CardHeader>
                  <Badge variant="secondary" className="w-fit font-mono">
                    catalog:read
                  </Badge>
                  <CardDescription className="mt-2">
                    Search the catalog across merchants.
                  </CardDescription>
                </CardHeader>
              </Card>
              <Card className="flex-1 basis-56">
                <CardHeader>
                  <Badge variant="secondary" className="w-fit font-mono">
                    product:read
                  </Badge>
                  <CardDescription className="mt-2">
                    Fetch a single product by ID.
                  </CardDescription>
                </CardHeader>
              </Card>
            </div>
          </section>

          <section id="search" className="scroll-mt-24 space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <Badge>GET</Badge>
              <h2 className="font-mono text-lg font-semibold tracking-tight">
                /api/v1/agent/catalog/search
              </h2>
            </div>
            <p className="text-muted-foreground">
              Search active, agent-searchable products across every
              merchant. Requires the{" "}
              <code className="rounded bg-muted px-1 py-0.5">catalog:read</code>{" "}
              scope.
            </p>

            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 text-left">
                  <tr>
                    <th className="px-4 py-2 font-medium">Parameter</th>
                    <th className="px-4 py-2 font-medium">Type</th>
                    <th className="px-4 py-2 font-medium">Description</th>
                  </tr>
                </thead>
                <tbody>
                  {searchParams.map((p) => (
                    <tr key={p.name} className="border-t">
                      <td className="px-4 py-2 font-mono">{p.name}</td>
                      <td className="px-4 py-2 text-muted-foreground">{p.type}</td>
                      <td className="px-4 py-2 text-muted-foreground">
                        {p.description}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <p className="text-sm font-medium">Example request</p>
            <CodeBlock>{`curl "https://api.yourdomain.com/api/v1/agent/catalog/search?q=keyboard&max_price=500000&in_stock=true" \\
  -H "Authorization: Bearer ac_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"`}</CodeBlock>

            <p className="text-sm font-medium">Example response</p>
            <CodeBlock>{`{
  "success": true,
  "data": [
    {
      "product_id": "b3c1f2b0-...",
      "merchant": { "merchant_id": "7a08...", "name": "TechStore" },
      "store": { "store_id": "005c...", "name": "Tech Store", "currency": "INR" },
      "name": "Mechanical Keyboard K8",
      "description": "Mechanical keyboard suitable for programming",
      "brand": "KeyPro",
      "category": "Keyboards",
      "images": [{ "url": "https://...", "is_primary": true }],
      "variants": [
        {
          "variant_id": "9e21...",
          "name": "Black / Red Switch",
          "sku": "K8-BLACK-RED",
          "price": { "amount": 479900, "currency": "INR" },
          "compare_at_price": null,
          "availability": "IN_STOCK",
          "stock_quantity": 25
        }
      ],
      "agent_searchable": true
    }
  ],
  "meta": { "total": 1, "limit": 20, "offset": 0, "has_more": false }
}`}</CodeBlock>
          </section>

          <section id="product" className="scroll-mt-24 space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <Badge>GET</Badge>
              <h2 className="font-mono text-lg font-semibold tracking-tight">
                /api/v1/agent/products/{"{product_id}"}
              </h2>
            </div>
            <p className="text-muted-foreground">
              Fetch a single product in the agent-readable format. Requires
              the <code className="rounded bg-muted px-1 py-0.5">product:read</code>{" "}
              scope. Returns{" "}
              <code className="rounded bg-muted px-1 py-0.5">404 PRODUCT_NOT_FOUND</code>{" "}
              if the product isn&apos;t <code className="rounded bg-muted px-1 py-0.5">ACTIVE</code> or
              isn&apos;t agent-searchable.
            </p>
            <p className="text-sm font-medium">Example request</p>
            <CodeBlock>{`curl "https://api.yourdomain.com/api/v1/agent/products/b3c1f2b0-1234-4a5b-9c6d-abcdef123456" \\
  -H "Authorization: Bearer ac_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"`}</CodeBlock>
          </section>

          <section id="format" className="scroll-mt-24 space-y-4">
            <h2 className="text-2xl font-semibold tracking-tight">
              Agent-readable format
            </h2>
            <p className="text-muted-foreground">
              Every product — from search or the single-product endpoint —
              follows this same fixed shape, so agents can rely on it
              without per-merchant special-casing.
            </p>
            <ul className="ml-5 list-disc space-y-1.5 text-sm text-muted-foreground">
              <li>
                Money is always an object:{" "}
                <code className="rounded bg-muted px-1 py-0.5">
                  {"{ amount, currency }"}
                </code>
                . <code className="rounded bg-muted px-1 py-0.5">amount</code>{" "}
                is an integer in the smallest currency unit — e.g. paise for
                INR, so ₹4,799.00 is <code className="rounded bg-muted px-1 py-0.5">479900</code>.
              </li>
              <li>
                <code className="rounded bg-muted px-1 py-0.5">availability</code>{" "}
                is one of <code className="rounded bg-muted px-1 py-0.5">IN_STOCK</code>,{" "}
                <code className="rounded bg-muted px-1 py-0.5">OUT_OF_STOCK</code>, or{" "}
                <code className="rounded bg-muted px-1 py-0.5">DISCONTINUED</code>.
              </li>
              <li>
                <code className="rounded bg-muted px-1 py-0.5">category</code>{" "}
                is the product&apos;s primary category name, or{" "}
                <code className="rounded bg-muted px-1 py-0.5">null</code>.
              </li>
              <li>
                Only products with <code className="rounded bg-muted px-1 py-0.5">status: ACTIVE</code> and{" "}
                <code className="rounded bg-muted px-1 py-0.5">agent_searchable: true</code> are ever
                returned through this API.
              </li>
            </ul>
          </section>

          <section id="errors" className="scroll-mt-24 space-y-4">
            <h2 className="text-2xl font-semibold tracking-tight">Errors</h2>
            <p className="text-muted-foreground">
              All errors share the same envelope:
            </p>
            <CodeBlock>{`{
  "success": false,
  "error": { "code": "PRODUCT_NOT_FOUND", "message": "Product not found" }
}`}</CodeBlock>
            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 text-left">
                  <tr>
                    <th className="px-4 py-2 font-medium">Status</th>
                    <th className="px-4 py-2 font-medium">Code</th>
                    <th className="px-4 py-2 font-medium">Meaning</th>
                  </tr>
                </thead>
                <tbody>
                  {errorCodes.map((e) => (
                    <tr key={e.code} className="border-t">
                      <td className="px-4 py-2 font-mono">{e.status}</td>
                      <td className="px-4 py-2 font-mono">{e.code}</td>
                      <td className="px-4 py-2 text-muted-foreground">
                        {e.meaning}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </main>
      </div>

      <footer className="border-t py-8">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-6 text-sm text-muted-foreground sm:flex-row">
          <span>&copy; {new Date().getFullYear()} Agentic Commerce</span>
          <span>Commerce, made agent-readable.</span>
        </div>
      </footer>
    </div>
  );
}
