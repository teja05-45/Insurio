# Design System

## 1. Direction

Insurio should read as a professional insurance-technology product, not a generic dashboard. The
interface is light, calm and text-first: policies are dense documents, so the UI avoids competing
ornament. Inspiration is drawn from Linear, Stripe, Vercel and Perplexity, but no template was used.

Principles:

1. **Evidence is visible.** Citations, pages, confidence and "Not stated" labels are first-class
   content, not tooltips.
2. **One accent.** AI blue signals interaction and intelligence; everything else is neutral.
3. **Text before chrome.** Typography and spacing carry hierarchy; shadows are subtle and few.
4. **No dead ends.** Every screen has loading, empty, error and success states, and every button
   performs a real action.

## 2. Tokens

Defined as CSS variables in `app/globals.css` and mapped into Tailwind (`tailwind.config.ts`).

| Token | Value | Use |
|---|---|---|
| `--background` | `hsl(210 40% 99%)` | App background |
| `--card` | `0 0% 100%` | Cards, composer, sheets |
| `--foreground` | `hsl(222 47% 11%)` | Primary text |
| `--muted-foreground` | `hsl(215 16% 47%)` | Secondary text, metadata |
| `--border` | `hsl(214 32% 91%)` | Dividers, input borders |
| `--primary` | `hsl(221 83% 53%)` | Actions, links, active nav, data emphasis |
| `--success` | `hsl(152 66% 32%)` | Ready, found, valid |
| `--warning` | `hsl(32 90% 40%)` | Processing, ambiguous, insufficient evidence |
| `--danger` | `hsl(0 72% 48%)` | Failed, destructive actions |

Radius scale: 8 px controls, 12 px cards, 20 px feature panels. Shadow `card` is a 1 px hairline plus
a low-opacity lift; `lift` is used only on hover or the hero mock.

Typography uses the system UI stack (no network font fetch at build time). Sizes: 12 px metadata,
14 px body and controls, 16–18 px section titles, 28–48 px marketing headings. Line height 1.6–1.7
for reading surfaces.

## 3. Components

`components/ui.tsx` provides `Button` (primary, secondary, ghost, outline, danger), `Input`,
`Textarea`, `Field`, `Card`, `Badge`, `StatusBadge`, `Spinner`, `Skeleton`, `EmptyState`,
`ErrorState`, `PageHeader` and `cn`.

Feature components: `AppShell` (responsive sidebar and mobile drawer), `AuthShell`, `UploadButton`,
`Markdown`, `CitationList`, `VoiceButton`, `Reveal` (framer-motion with reduced-motion respect).

Status is always shown with a label, not colour alone: `Ready`, `Processing`, `Failed`, `Queued`,
`Found`, `Ambiguous`, `Not stated`.

## 4. Screen composition

| Screen | Composition |
|---|---|
| Landing | Sticky header, hero with an illustrative chat mock, six capabilities, three-step workflow, evidence explanation, security panel, CTA, footer |
| Auth | Split layout: form on the left, product principles on the right; collapses to a single column |
| Dashboard | Four stat cards, recent documents, recent conversations, comparison prompt |
| Documents | Filter row, full-width list with status, metadata, insights/chat/delete actions |
| Workspace | Header with actions, live processing progress, tabs for extracted text and PDF, page list, page navigation |
| Insights | Coverage chart, counts, grouped field cards with quote, page and confidence |
| Chat | History column on desktop, streaming transcript, composer with voice and stop, citation accordions, evidence groups, feedback |
| Compare | Policy selection, saved comparison chips, field-by-field table with per-side evidence |
| Settings | Profile, security, sessions, usage, deployment capabilities, danger zone |

## 5. Responsive behaviour

- 360 px: single column; sidebar becomes a drawer; tables scroll horizontally; chat header wraps.
- 768 px: two-column card grids; document rows remain stacked but actions align.
- 1024 px+: persistent 256 px sidebar; chat adds a history column; insights and compare use their
  full two-column composition.

The landing hero mock is labelled "Illustrative interface", so it is never mistaken for a screenshot
of a real policy.

## 6. Accessibility

- Semantic landmarks (`header`, `nav`, `main`, `aside`), one `h1` per page, ordered headings.
- All icon-only controls have `aria-label` and a `title`; the mobile menu reports `aria-expanded`.
- Filters and toggles use `aria-pressed` / `aria-selected`; streaming regions use `aria-live`.
- Visible focus ring via `:focus-visible`; all interactive elements are keyboard reachable.
- Colour contrast target is WCAG AA; status is never encoded by colour alone.
- `prefers-reduced-motion` disables animations and transitions globally, and `Reveal` short-circuits.
- Forms pair every input with a `<label>` and surface errors with `role="alert"`.

## 7. Content rules

- Say "Not stated" rather than leaving a field blank; never imply inferred coverage.
- Keep the disclaimer visible in chat and the footer: informational analysis, not insurance advice.
- Avoid exclamation marks and marketing superlatives inside the product.
- Numbers keep their document formatting (for example `Rs. 500000`) so they can be checked against
  the page.
