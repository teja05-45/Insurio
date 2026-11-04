"""
modules/sanitize.py
───────────────────
Output sanitization for PolicyPilot AI.

Two concerns are handled here:

1. LLM response sanitization
   The model occasionally returns HTML markup (tags, entities, inline styles).
   Before any response is stored in session state or rendered, it is passed
   through `sanitize_llm_response()` which strips every HTML tag and decodes
   HTML entities so only plain text / Markdown reaches the chat bubble.

2. RAG context sanitization
   If a PDF was converted from a web page it may contain raw HTML fragments.
   `sanitize_rag_context()` strips those fragments before the chunks are sent
   to the model, preventing the model from "learning" to echo HTML back.
"""

import re
import html


# ─── Compiled patterns (built once at import) ────────────────────────────────

# Matches any HTML / XML tag: <div>, </div>, <br/>, <!-- comment -->, etc.
_TAG_RE = re.compile(r"<[^>]+>", re.DOTALL)

# Matches sequences of HTML entities: &nbsp; &#160; &amp; &#x2F; etc.
_ENTITY_RE = re.compile(r"&[a-zA-Z#][a-zA-Z0-9]{1,6};")

# Collapse 3+ blank lines that stripping tags can leave behind
_BLANK_LINES_RE = re.compile(r"\n{3,}")

# Inline CSS / style attributes sometimes appear as plain text after tag removal
_STYLE_ATTR_RE = re.compile(
    r'style\s*=\s*["\'][^"\']*["\']', re.IGNORECASE
)

# Common HTML boilerplate strings that occasionally bleed through
_BOILERPLATE_RE = re.compile(
    r"<!DOCTYPE[^>]*>|<html[^>]*>|<head[^>]*>|<body[^>]*>",
    re.IGNORECASE,
)


# ─── Public API ───────────────────────────────────────────────────────────────

def sanitize_llm_response(text: str) -> str:
    """
    Strip all HTML from a raw LLM response and return clean Markdown / plain text.

    Steps
    -----
    1. Remove HTML boilerplate declarations.
    2. Remove every HTML tag.
    3. Decode HTML entities (e.g. &amp; → &, &lt; → <).
    4. Remove any dangling style="…" attribute strings.
    5. Normalise whitespace.

    The function is intentionally conservative: it never removes content that
    is not HTML.  Markdown syntax (**, *, #, >, -, etc.) is preserved intact.

    Parameters
    ----------
    text : str
        Raw string returned by the Groq API.

    Returns
    -------
    str
        Sanitized string safe to render with ``st.markdown(text)``
        (i.e. *without* ``unsafe_allow_html=True``).
    """
    if not text:
        return ""

    # 1. Boilerplate
    text = _BOILERPLATE_RE.sub("", text)

    # 2. Decode entities FIRST so that &lt;script&gt; becomes <script>
    #    before the tag stripper runs — catches entity-encoded HTML tags
    text = html.unescape(text)

    # 3. Strip all tags (catches both literal and previously-encoded tags)
    text = _TAG_RE.sub("", text)

    # 4. Remove dangling style attributes
    text = _STYLE_ATTR_RE.sub("", text)

    # 5. Normalise whitespace
    text = _BLANK_LINES_RE.sub("\n\n", text)
    text = text.strip()

    return text


def sanitize_rag_context(context: str) -> str:
    """
    Strip HTML from retrieved document chunks before sending them to the LLM.

    This prevents two problems:
    - The model seeing HTML markup in its context and echoing it back.
    - Token budget being wasted on markup instead of content.

    Parameters
    ----------
    context : str
        Raw context string assembled from vector-store chunks.

    Returns
    -------
    str
        HTML-free context string.
    """
    if not context:
        return ""

    context = _BOILERPLATE_RE.sub("", context)
    context = html.unescape(context)       # decode entities before stripping tags
    context = _TAG_RE.sub("", context)
    context = _STYLE_ATTR_RE.sub("", context)
    context = _BLANK_LINES_RE.sub("\n\n", context)
    return context.strip()


def escape_for_html_bubble(text: str) -> str:
    """
    Safely escape user-supplied or LLM-generated text before it is
    interpolated into a hand-crafted HTML string (e.g. a chat bubble built
    with f-strings).

    Use this whenever you are building HTML manually with unsafe_allow_html=True
    and need to embed dynamic content inside it.

    Parameters
    ----------
    text : str
        Any string that will appear inside an HTML attribute or element.

    Returns
    -------
    str
        HTML-escaped string.  <, >, &, " and ' are replaced with entities.
    """
    return html.escape(text, quote=True)