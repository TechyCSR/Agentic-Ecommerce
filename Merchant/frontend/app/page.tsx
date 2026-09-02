import { Show } from "@clerk/nextjs";
import {
  ArrowRight,
  Bot,
  KeyRound,
  LayoutGrid,
  Package,
  ShieldCheck,
  Sparkles,
  Store,
} from "lucide-react";
import Link from "next/link";

import { Logo } from "@/components/brand/logo";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const TAGLINE = "Commerce, made agent-readable.";

const features = [
  {
    icon: LayoutGrid,
    title: "Merchant & Catalog Management",
    description:
      "Create your store, manage products, variants, images, and inventory from a single dashboard.",
  },
  {
    icon: Bot,
    title: "Agent-Ready Catalog",
    description:
      "Every active product is exposed through a standardized, agent-readable format ready for AI shopping agents.",
  },
  {
    icon: ShieldCheck,
    title: "Secure API Access",
    description:
      "Issue scoped API keys for authorized agents and partners. Keys are hashed and shown only once.",
  },
];

const steps = [
  {
    step: "01",
    icon: Store,
    title: "Create your store",
    description: "Set up a merchant profile and store in under a minute.",
  },
  {
    step: "02",
    icon: Package,
    title: "Add your products",
    description: "List products with variants, pricing, images and stock.",
  },
  {
    step: "03",
    icon: Sparkles,
    title: "Mark them agent-ready",
    description: "Flag active listings as searchable by AI shopping agents.",
  },
  {
    step: "04",
    icon: KeyRound,
    title: "Issue a secure API key",
    description: "Grant scoped, revocable access to authorized agents.",
  },
];

export default function Home() {
  return (
    <div className="flex flex-1 flex-col">
      <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur supports-backdrop-filter:bg-background/60">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link href="/" aria-label="Agentic Commerce home">
            <Logo />
          </Link>
          <div className="flex items-center gap-3">
            <Show when="signed-out">
              <Button variant="ghost" render={<Link href="/sign-in" />}>
                Sign in
              </Button>
              <Button render={<Link href="/sign-up" />}>
                Get started <ArrowRight className="size-4" />
              </Button>
            </Show>
            <Show when="signed-in">
              <Button render={<Link href="/dashboard" />}>Go to Dashboard</Button>
            </Show>
          </div>
        </div>
      </header>

      <main className="flex-1">
        {/* Hero */}
        <section className="relative overflow-hidden">
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 -z-10 mask-[radial-gradient(ellipse_60%_50%_at_50%_0%,black,transparent)]"
          >
            <div className="absolute left-1/2 top-[-10%] size-144 -translate-x-1/2 rounded-full bg-linear-to-br from-indigo-500/20 via-violet-500/10 to-transparent blur-3xl" />
          </div>

          <div className="mx-auto max-w-6xl px-6 pb-20 pt-20 sm:pt-28">
            <div className="mx-auto max-w-3xl text-center">
              <div className="mx-auto mb-6 inline-flex items-center gap-2 rounded-full border bg-muted/50 px-3 py-1 text-xs font-medium text-muted-foreground">
                <Sparkles className="size-3 text-indigo-500" />
                {TAGLINE}
              </div>
              <h1 className="text-4xl font-bold tracking-tight text-balance sm:text-5xl lg:text-6xl">
                The commerce foundation for{" "}
                <span className="bg-linear-to-br from-indigo-500 to-violet-600 bg-clip-text text-transparent">
                  AI shopping agents
                </span>
              </h1>
              <p className="mx-auto mt-5 max-w-2xl text-lg text-balance text-muted-foreground">
                Onboard your store, manage your catalog, and securely expose
                your products to authorized AI agents through a standardized,
                versioned API.
              </p>
              <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
                <Show when="signed-out">
                  <Button size="lg" render={<Link href="/sign-up" />}>
                    Start selling <ArrowRight className="size-4" />
                  </Button>
                  <Button
                    size="lg"
                    variant="outline"
                    render={<Link href="/sign-in" />}
                  >
                    Sign in
                  </Button>
                </Show>
                <Show when="signed-in">
                  <Button size="lg" render={<Link href="/dashboard" />}>
                    Open Dashboard <ArrowRight className="size-4" />
                  </Button>
                </Show>
              </div>
            </div>
          </div>
        </section>

        {/* How it works */}
        <section className="border-t bg-muted/20 py-20">
          <div className="mx-auto max-w-6xl px-6">
            <div className="mx-auto max-w-2xl text-center">
              <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
                From sign-up to agent-ready in four steps
              </h2>
              <p className="mt-3 text-muted-foreground">
                Everything a merchant needs to get discovered by AI shopping
                agents, without the busywork.
              </p>
            </div>
            <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {steps.map((s) => (
                <div
                  key={s.step}
                  className="relative rounded-xl border bg-background p-5"
                >
                  <span className="text-xs font-semibold text-muted-foreground/60">
                    {s.step}
                  </span>
                  <div className="mt-3 flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <s.icon className="size-4" />
                  </div>
                  <h3 className="mt-4 text-sm font-semibold">{s.title}</h3>
                  <p className="mt-1.5 text-sm text-muted-foreground">
                    {s.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Features */}
        <section className="py-20">
          <div className="mx-auto max-w-6xl px-6">
            <div className="mx-auto max-w-2xl text-center">
              <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
                Built for merchants and agents alike
              </h2>
            </div>
            <div className="mt-12 grid gap-6 sm:grid-cols-3">
              {features.map((feature) => (
                <Card
                  key={feature.title}
                  className="transition-shadow hover:shadow-md"
                >
                  <CardHeader>
                    <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      <feature.icon className="size-5" />
                    </div>
                    <CardTitle className="mt-3">{feature.title}</CardTitle>
                    <CardDescription>{feature.description}</CardDescription>
                  </CardHeader>
                </Card>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="pb-20">
          <div className="mx-auto max-w-6xl px-6">
            <div className="relative overflow-hidden rounded-2xl border bg-linear-to-br from-indigo-500 to-violet-600 px-8 py-14 text-center text-white sm:px-16">
              <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
                Ready to make your catalog agent-ready?
              </h2>
              <p className="mx-auto mt-3 max-w-xl text-indigo-100">
                Create your merchant profile and start listing products in
                minutes &mdash; no credit card required.
              </p>
              <div className="mt-8 flex items-center justify-center gap-3">
                <Show when="signed-out">
                  <Button
                    size="lg"
                    className="bg-white text-indigo-700 hover:bg-white/90"
                    render={<Link href="/sign-up" />}
                  >
                    Get started free <ArrowRight className="size-4" />
                  </Button>
                </Show>
                <Show when="signed-in">
                  <Button
                    size="lg"
                    className="bg-white text-indigo-700 hover:bg-white/90"
                    render={<Link href="/dashboard" />}
                  >
                    Open Dashboard <ArrowRight className="size-4" />
                  </Button>
                </Show>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t py-8">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-6 text-sm text-muted-foreground sm:flex-row">
          <span>&copy; {new Date().getFullYear()} Agentic Commerce</span>
          <span>{TAGLINE}</span>
        </div>
      </footer>
    </div>
  );
}
