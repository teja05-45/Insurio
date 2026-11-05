import Link from "next/link";
import { ShieldCheck } from "lucide-react";

export function AuthShell({
  title,
  description,
  children,
  footer,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  return (
    <div className="grid min-h-dvh lg:grid-cols-[1.05fr_0.95fr]">
      <div className="flex flex-col justify-center px-5 py-10 sm:px-10 lg:px-16">
        <div className="mx-auto w-full max-w-sm">
          <Link href="/" className="mb-10 inline-flex items-center gap-2 font-semibold">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <ShieldCheck size={18} aria-hidden />
            </span>
            Insurio
          </Link>
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          <p className="mt-2 text-sm text-muted-foreground">{description}</p>
          <div className="mt-7">{children}</div>
          {footer ? <div className="mt-6 text-sm text-muted-foreground">{footer}</div> : null}
        </div>
      </div>

      <div className="relative hidden overflow-hidden border-l border-border bg-white lg:block">
        <div
          aria-hidden
          className="absolute inset-0"
          style={{
            backgroundImage:
              "radial-gradient(540px 320px at 30% 10%, hsl(221 83% 53% / 0.12), transparent), radial-gradient(420px 300px at 80% 80%, hsl(199 89% 48% / 0.10), transparent)",
          }}
        />
        <div className="relative flex h-full flex-col justify-center px-14">
          <blockquote className="max-w-md text-lg font-medium leading-relaxed text-foreground">
            &ldquo;Is this procedure covered, and which waiting period applies?&rdquo;
          </blockquote>
          <p className="mt-3 max-w-md text-sm leading-relaxed text-muted-foreground">
            Insurio answers from your policy with the exact page and clause attached — and says so
            when the document is silent.
          </p>
          <div className="mt-8 space-y-2.5">
            {[
              ["Page-accurate extraction", "Heading-aware chunks keep every clause traceable."],
              ["Validated citations", "Quotes are checked against the retrieved text."],
              ["Private by default", "Documents are scoped to your account."],
            ].map(([title, body]) => (
              <div
                key={title}
                className="rounded-lg border border-border bg-white/80 px-4 py-3 shadow-sm backdrop-blur"
              >
                <p className="text-xs font-semibold text-foreground">{title}</p>
                <p className="mt-0.5 text-xs text-muted-foreground">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
