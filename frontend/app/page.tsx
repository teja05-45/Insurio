import Link from "next/link";
import {
  ArrowRight,
  BookOpenCheck,
  Check,
  FileText,
  GitCompareArrows,
  Lock,
  MessagesSquare,
  Mic,
  Quote,
  Search,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { Reveal } from "@/components/Reveal";

const CAPABILITIES = [
  {
    icon: Search,
    title: "Hybrid retrieval",
    body: "BM25 and semantic scoring are fused, so both exact clauses and paraphrased questions find the right pages.",
  },
  {
    icon: Quote,
    title: "Verified citations",
    body: "Every quote is checked against the retrieved page. Invented clauses are dropped and the answer is flagged.",
  },
  {
    icon: BookOpenCheck,
    title: "Policy intelligence",
    body: "Sum insured, deductibles, waiting periods, sub-limits and claim steps, each with its source and page.",
  },
  {
    icon: GitCompareArrows,
    title: "Field-by-field comparison",
    body: "Compare two to five policies on structured values, with the exact wording behind each difference.",
  },
  {
    icon: MessagesSquare,
    title: "Conversation memory",
    body: "Ask follow-ups in context. Every answer, citation and confidence score is saved to your account.",
  },
  {
    icon: Mic,
    title: "Voice questions",
    body: "Dictate a question with your browser's speech recognition. Audio is never uploaded or stored.",
  },
];

const STEPS = [
  {
    title: "Upload the policy",
    body: "Validated, page-accurate text extraction with heading-aware chunking. Scanned documents can use OCR.",
  },
  {
    title: "Read the evidence",
    body: "Insights are extracted with a source quote, page number, confidence and an explicit status for missing fields.",
  },
  {
    title: "Ask anything",
    body: "Answers stream from your document only. Each claim separates what is stated, inferred, and not in the policy.",
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-dvh bg-background">
      <header className="sticky top-0 z-40 border-b border-border/80 bg-background/85 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5">
          <Link href="/" className="flex items-center gap-2 font-semibold">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <ShieldCheck size={18} aria-hidden />
            </span>
            <span className="tracking-tight">Insurio</span>
          </Link>
          <nav className="hidden items-center gap-7 text-sm text-muted-foreground md:flex">
            <a href="#capabilities" className="transition-colors hover:text-foreground">
              Capabilities
            </a>
            <a href="#how-it-works" className="transition-colors hover:text-foreground">
              How it works
            </a>
            <a href="#security" className="transition-colors hover:text-foreground">
              Security
            </a>
          </nav>
          <div className="flex items-center gap-2">
            <Link
              href="/login"
              className="rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              Sign in
            </Link>
            <Link
              href="/register"
              className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-primary px-4 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
            >
              Get started
              <ArrowRight size={15} aria-hidden />
            </Link>
          </div>
        </div>
      </header>

      <main>
        <section className="relative overflow-hidden border-b border-border/70">
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 opacity-70"
            style={{
              backgroundImage:
                "radial-gradient(600px 320px at 18% 0%, hsl(221 83% 53% / 0.10), transparent), radial-gradient(500px 300px at 85% 20%, hsl(199 89% 48% / 0.08), transparent)",
            }}
          />
          <div className="relative mx-auto grid max-w-6xl gap-12 px-5 py-16 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:py-24">
            <div>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-white px-3 py-1 text-xs font-medium text-muted-foreground shadow-sm">
                <Sparkles size={13} className="text-primary" aria-hidden />
                Evidence-grounded policy analysis
              </span>
              <h1 className="mt-5 text-4xl font-semibold leading-[1.1] tracking-tight text-foreground sm:text-5xl">
                Understand what your insurance actually covers.
              </h1>
              <p className="mt-5 max-w-xl text-base leading-relaxed text-muted-foreground">
                Insurio reads your policy PDF and answers questions about coverage, exclusions,
                waiting periods and claims — with a page-level citation for every claim it makes.
                No general-knowledge guesses.
              </p>
              <div className="mt-7 flex flex-wrap items-center gap-3">
                <Link
                  href="/register"
                  className="inline-flex h-11 items-center gap-2 rounded-lg bg-primary px-5 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
                >
                  Analyse a policy
                  <ArrowRight size={16} aria-hidden />
                </Link>
                <Link
                  href="/login"
                  className="inline-flex h-11 items-center rounded-lg border border-border bg-white px-5 text-sm font-medium text-foreground shadow-sm transition-colors hover:bg-muted"
                >
                  Sign in
                </Link>
              </div>
              <ul className="mt-7 flex flex-wrap gap-x-6 gap-y-2 text-xs text-muted-foreground">
                {["Document-scoped answers", "Quotes verified server-side", "Delete your data anytime"].map(
                  (item) => (
                    <li key={item} className="flex items-center gap-1.5">
                      <Check size={13} className="text-success" aria-hidden />
                      {item}
                    </li>
                  ),
                )}
              </ul>
            </div>

            <Reveal className="lg:justify-self-end">
              <div className="w-full max-w-md rounded-2xl border border-border bg-white p-1.5 shadow-lift">
                <div className="rounded-xl border border-border/70 bg-background/60">
                  <div className="flex items-center justify-between border-b border-border/70 px-4 py-3">
                    <div className="flex items-center gap-2 text-xs font-medium text-foreground">
                      <FileText size={14} className="text-primary" aria-hidden />
                      health-policy-2026.pdf
                    </div>
                    <span className="rounded-full bg-success/10 px-2 py-0.5 text-[11px] font-medium text-success">
                      Ready
                    </span>
                  </div>
                  <div className="space-y-3 p-4">
                    <div className="ml-auto w-fit max-w-[85%] rounded-xl rounded-br-sm bg-primary px-3 py-2 text-xs text-primary-foreground">
                      Is knee replacement covered, and what is the waiting period?
                    </div>
                    <div className="max-w-[92%] rounded-xl rounded-bl-sm border border-border bg-white px-3 py-2.5 text-xs leading-relaxed text-foreground shadow-sm">
                      <p>
                        <strong>Yes — subject to a 24-month waiting period.</strong> Joint
                        replacement is listed under planned procedures{" "}
                        <span className="font-medium text-primary">[S1]</span> and carries a
                        disease-specific waiting period{" "}
                        <span className="font-medium text-primary">[S2]</span>.
                      </p>
                      <div className="mt-3 space-y-1.5 border-t border-border pt-2.5">
                        <div className="flex items-center gap-2 rounded-md bg-muted/70 px-2 py-1.5">
                          <span className="text-[10px] font-semibold text-primary">S1</span>
                          <span className="text-[11px] text-muted-foreground">
                            page 12 · &ldquo;Joint replacement surgery…&rdquo;
                          </span>
                        </div>
                        <div className="flex items-center gap-2 rounded-md bg-muted/70 px-2 py-1.5">
                          <span className="text-[10px] font-semibold text-primary">S2</span>
                          <span className="text-[11px] text-muted-foreground">
                            page 18 · &ldquo;24 months from inception…&rdquo;
                          </span>
                        </div>
                      </div>
                    </div>
                    <p className="text-center text-[10px] text-muted-foreground">
                      Illustrative interface · answers depend on your document
                    </p>
                  </div>
                </div>
              </div>
            </Reveal>
          </div>
        </section>

        <section id="capabilities" className="border-b border-border/70 py-16">
          <div className="mx-auto max-w-6xl px-5">
            <Reveal>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">
                Capabilities
              </p>
              <h2 className="mt-2 max-w-2xl text-2xl font-semibold tracking-tight sm:text-3xl">
                Built for the questions policies are bad at answering.
              </h2>
            </Reveal>
            <div className="mt-9 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {CAPABILITIES.map((capability, index) => (
                <Reveal key={capability.title} delay={index * 0.04}>
                  <div className="h-full rounded-xl border border-border bg-card p-5 shadow-card transition-shadow hover:shadow-lift">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      <capability.icon size={17} aria-hidden />
                    </div>
                    <h3 className="mt-4 text-sm font-semibold text-foreground">
                      {capability.title}
                    </h3>
                    <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
                      {capability.body}
                    </p>
                  </div>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        <section id="how-it-works" className="border-b border-border/70 py-16">
          <div className="mx-auto max-w-6xl px-5">
            <div className="grid gap-10 lg:grid-cols-[0.85fr_1.15fr]">
              <Reveal>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">
                  How it works
                </p>
                <h2 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">
                  Three steps from PDF to a defensible answer.
                </h2>
                <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
                  Processing runs in the background, so the upload returns immediately. Nothing is
                  embedded from outside your document, and no answer is generated without retrieved
                  evidence.
                </p>
              </Reveal>
              <div className="space-y-3">
                {STEPS.map((step, index) => (
                  <Reveal key={step.title} delay={index * 0.05}>
                    <div className="flex gap-4 rounded-xl border border-border bg-card p-5 shadow-card">
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
                        {index + 1}
                      </span>
                      <div>
                        <h3 className="text-sm font-semibold">{step.title}</h3>
                        <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                          {step.body}
                        </p>
                      </div>
                    </div>
                  </Reveal>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="border-b border-border/70 bg-white py-16">
          <div className="mx-auto grid max-w-6xl gap-10 px-5 lg:grid-cols-2 lg:items-center">
            <Reveal>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">
                Grounded by design
              </p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">
                Every answer shows its work.
              </h2>
              <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
                A policy assistant that sounds confident is not useful. Insurio separates what the
                document states from interpretation, and says plainly when the information is not
                there.
              </p>
              <ul className="mt-5 space-y-3 text-sm">
                {[
                  "Quotes are validated against the retrieved page before they are shown.",
                  "Unsupported citations are removed and the answer is marked as flagged.",
                  "Missing clauses produce an explicit insufficient-evidence response.",
                ].map((item) => (
                  <li key={item} className="flex gap-2.5 text-muted-foreground">
                    <Check size={16} className="mt-0.5 shrink-0 text-success" aria-hidden />
                    {item}
                  </li>
                ))}
              </ul>
            </Reveal>
            <Reveal delay={0.05}>
              <div className="rounded-xl border border-border bg-background p-5 shadow-card">
                <div className="grid gap-3 sm:grid-cols-3">
                  {[
                    {
                      title: "Stated",
                      tone: "text-success bg-success/10",
                      body: "“Cosmetic surgery is excluded from coverage.”",
                    },
                    {
                      title: "Inferred",
                      tone: "text-warning bg-warning/10",
                      body: "A related clause suggests an exception after an accident.",
                    },
                    {
                      title: "Not in document",
                      tone: "text-danger bg-danger/10",
                      body: "Maternity waiting period is not stated.",
                    },
                  ].map((item) => (
                    <div key={item.title} className="rounded-lg border border-border bg-white p-3">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${item.tone}`}
                      >
                        {item.title}
                      </span>
                      <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
                        {item.body}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </Reveal>
          </div>
        </section>

        <section id="security" className="border-b border-border/70 py-16">
          <div className="mx-auto max-w-6xl px-5">
            <div className="rounded-2xl border border-border bg-card p-8 shadow-card sm:p-10">
              <div className="grid gap-8 lg:grid-cols-[0.9fr_1.1fr]">
                <div>
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                    <Lock size={19} aria-hidden />
                  </div>
                  <h2 className="mt-4 text-2xl font-semibold tracking-tight">
                    Your policies stay yours.
                  </h2>
                  <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                    Documents are stored under server-generated identifiers, served only to the
                    account that uploaded them, and never used to train a model.
                  </p>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  {[
                    ["Per-account isolation", "Every query is scoped to the owner."],
                    ["Validated uploads", "Magic-byte, size, page and encrypt checks."],
                    ["Short-lived sessions", "Rotating, revocable refresh tokens."],
                    ["Prompt-injection defence", "Document text is data, never instructions."],
                  ].map(([title, body]) => (
                    <div key={title} className="rounded-lg border border-border bg-background p-4">
                      <h3 className="text-sm font-medium">{title}</h3>
                      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{body}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="py-16">
          <div className="mx-auto max-w-3xl px-5 text-center">
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
              Know what you are covered for before you need it.
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-sm text-muted-foreground">
              Create an account, upload a policy and ask your first question in under a minute.
            </p>
            <div className="mt-6 flex justify-center">
              <Link
                href="/register"
                className="inline-flex h-11 items-center gap-2 rounded-lg bg-primary px-5 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
              >
                Create your workspace
                <ArrowRight size={16} aria-hidden />
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-border bg-white">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-5 py-8 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck size={15} className="text-primary" aria-hidden />
            <span className="font-medium text-foreground">Insurio</span>
            <span>AI policy intelligence</span>
          </div>
          <p>
            Informational tool, not insurance or legal advice. Confirm coverage with your insurer.
          </p>
        </div>
      </footer>
    </div>
  );
}
