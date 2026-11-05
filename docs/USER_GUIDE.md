# User Guide

## 1. Create an account

Open the site and choose **Get started**. Enter your name, email, and a password of at least 10
characters containing a letter and a number. You are signed in immediately.

Forgot your password? Use the link on the sign-in page. On this deployment the reset token is shown
on screen because email delivery is not configured; the same flow applies with email later.

## 2. Upload a policy

Choose **Upload policy** on the dashboard or documents page and select a PDF.

- Maximum 20 MB and 400 pages by default.
- The PDF must contain selectable text. Scanned images require OCR to be enabled by the operator.
- Duplicate uploads of the same file are rejected.

Processing runs in the background. The workspace shows progress and updates automatically. When the
status becomes **Ready**, extraction is complete.

## 3. Read the workspace

The workspace shows the document's pages, size, chunk count, and upload date.

- **Extracted text** — page by page, with previous/next navigation and a page list. This is the text
  the assistant uses, so you can check any answer against it.
- **PDF** — a preview of the original file. Use **Open in new tab** if the inline preview is
  unavailable. **Download** saves the file.
- Failed processing shows the reason and no partial results.

## 4. Policy insights

**Insights** turns the document into structured fields: policyholder, insurer, policy number and
type, insured members, sum insured, coverage, exclusions, waiting periods, deductible, co-payment,
room rent limit, sub-limits, pre-existing disease terms, maternity, renewal, grace period, claim
procedure, claim documents, and important conditions.

Each field shows its value, the exact quote, the page, and a confidence level. Three states matter:

- **Found** — stated in the document.
- **Ambiguous** — the document is unclear or contradictory; read the quote.
- **Not stated** — the document does not provide it. Insurio never guesses.

**Re-extract** re-runs extraction, for example after enabling a model for enrichment.

## 5. Ask questions

Open **Ask questions** from a document, or **Chat** from the sidebar.

Suggested first questions appear for a new conversation. Type, or use the microphone button where
the browser supports speech recognition; audio is not uploaded or stored.

While an answer streams you can stop it. Completed answers offer:

- **Sources** — every validated citation with its page and quote. Expand to read the clause.
- **Stated / Interpretation / Not in the document** — how each part of the answer relates to the
  policy.
- **Confidence** and citation status.
- **Copy**, **Regenerate**, **Helpful**, **Not helpful**.

If the policy does not contain the answer, Insurio says so explicitly instead of guessing.

Conversations are saved per document. Rename is available via the API; delete uses the trash icon in
the conversation list.

## 6. Compare policies

Open **Compare**, select two to five processed policies, and choose **Compare**. The table shows each
field side by side, marks where values differ, and lists evidence behind each value. "Not stated"
means that policy is silent on the field — often the most important difference.

Saved comparisons appear as chips above the table and can be deleted.

## 7. Settings

- **Profile** — update your name.
- **Account security** — change your password (this signs out all sessions).
- **Active sessions** — refresh grants with start/expiry time, client and IP.
- **Usage** — policy, conversation, question and comparison counts.
- **Deployment capabilities** — model, embedding mode, OCR, limits.
- **Danger zone** — delete your account and all associated data. This cannot be undone.

## 8. Privacy and limits

- Documents and conversations are visible only to your account.
- Answers come only from the uploaded document, not from general knowledge.
- Insurio is an informational tool. It does not sell insurance, decide claims, or give legal or
  medical advice. Confirm coverage with your insurer before acting.
- Answer quality depends on the PDF: tables, stamps and scanned pages can reduce accuracy.
