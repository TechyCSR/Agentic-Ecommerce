import { Show } from "@clerk/nextjs";
import { ArrowRight, Bot, LayoutGrid, ShieldCheck } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const features = [
  {
    icon: LayoutGrid,
    title: "Merchant &amp; Catalog Management",
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

export default function Home() {
  return (
    <div className="flex flex-1 flex-col">
      <header className="border-b">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <span className="text-lg font-semibold tracking-tight">
            Agentic Commerce
          </span>
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
        <section className="mx-auto max-w-6xl px-6 py-24 text-center">
          <h1 className="mx-auto max-w-3xl text-4xl font-bold tracking-tight sm:text-5xl">
            The commerce foundation for AI shopping agents
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground">
            Onboard your store, manage your catalog, and securely expose your
            products to authorized AI agents through a standardized API.
          </p>
          <div className="mt-8 flex items-center justify-center gap-3">
            <Show when="signed-out">
              <Button size="lg" render={<Link href="/sign-up" />}>
                Start selling <ArrowRight className="size-4" />
              </Button>
            </Show>
            <Show when="signed-in">
              <Button size="lg" render={<Link href="/dashboard" />}>
                Open Dashboard
              </Button>
            </Show>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-6 pb-24">
          <div className="grid gap-6 sm:grid-cols-3">
            {features.map((feature) => (
              <Card key={feature.title}>
                <CardHeader>
                  <feature.icon className="size-8 text-primary" />
                  <CardTitle className="mt-2">{feature.title}</CardTitle>
                  <CardDescription>{feature.description}</CardDescription>
                </CardHeader>
                <CardContent />
              </Card>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t py-6 text-center text-sm text-muted-foreground">
        Agentic Commerce Platform — Phase 1 Merchant Foundation
      </footer>
    </div>
  );
}
