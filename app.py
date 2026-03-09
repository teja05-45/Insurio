"""
Insurio — v4.0 "Conversation-First" redesign
─────────────────────────────────────────────────────
Layout: single-column, full-width conversation like ChatGPT / Perplexity.
No split-screen. Everything revolves around the chat thread.

Architecture:
    app.py               ← this file
    modules/
        groq_client.py   ← Groq LLM (LLaMA 3 / Mixtral)
        rag_pipeline.py  ← PDF parse, chunk, embed, retrieve
        voice_input.py   ← SpeechRecognition → text
        styles.py        ← CSS design system v4
        sanitize.py      ← strip HTML from LLM output / RAG context

Run:
    streamlit run app.py

CHAT STATE DESIGN
─────────────────
• st.chat_input() is called at the TOP of the main script body — NOT
  inside any column or nested container.  This gives Streamlit full
  control over its sticky-bottom placement and guarantees it resets to
  None on every rerun except the one the user triggered by pressing Send.

• Dispatch (_handle_question) runs BEFORE the render loop, so both the
  user message and the assistant reply are in chat_history by the time
  the render loop executes.  st.rerun() after dispatch ensures the UI
  reflects the new state immediately.

• voice_prefill is read and cleared before chat_input is evaluated.
  chat_input always wins; prefill is only used when chat_input is None.

• _handle_question() has an internal idempotency guard — identical
  consecutive questions are silently dropped before any LLM call.

INSIGHT CARDS
─────────────
After a policy is uploaded, generate_policy_insights() produces
structured Markdown text with ## SECTION headers.  _render_insight_cards()
parses those sections and renders them as styled HTML cards injected into
the conversation as the first assistant message.  Cards are defined in
CARD_DEFS — each maps a section key → (emoji, label, colour class).
"""

import re
import sys
import os

import streamlit as st

sys.path.insert(0, os.path.dirname(__file__))

from modules.styles import inject_styles
from modules.rag_pipeline import process_document, retrieve_context
from modules.groq_client import generate_answer, generate_policy_insights, get_api_key
from modules.voice_input import transcribe_audio, get_voice_status
from modules.sanitize import sanitize_llm_response, escape_for_html_bubble

# ─── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Insurio",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_styles()

# ─── Insight card definitions ─────────────────────────────────────────────────
# Each entry: section_key → (emoji, display_label, css_colour_class)
CARD_DEFS = {
    "COVERAGE SUMMARY":  ("📋", "Coverage Summary",  "blue"),
    "WAITING PERIODS":   ("⏳", "Waiting Periods",    "amber"),
    "KEY EXCLUSIONS":    ("🚫", "Key Exclusions",     "rose"),
    "IMPORTANT CLAUSES": ("📌", "Important Clauses",  "violet"),
    "RISK ANALYSIS":     ("⚠️",  "Risk Analysis",      "teal"),
}

# ─── Session state ────────────────────────────────────────────────────────────

def _init_state() -> None:
    defaults = {
        "vector_store":     None,
        "policy_text":      None,
        "policy_name":      None,
        "policy_pages":     0,
        "policy_chunks":    0,
        "policy_insights":  None,      # raw Markdown string from LLM
        "retrieval_method": "keyword",
        "chat_history":     [],        # [{"role":"user"|"assistant","content":str}]
        "voice_prefill":    "",        # one-shot prefill from voice transcription
        "insights_injected":False,     # True after cards are added to chat_history
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ─── Insight card builder ─────────────────────────────────────────────────────

def _build_insight_cards_html(insights_text: str) -> str:
    """
    Parse the structured LLM insight text and return an HTML string
    containing pp-icard div cards, laid out in a 2-column grid.

    Only cards that have matching content in insights_text are rendered.
    The HTML is safe to pass to st.markdown(unsafe_allow_html=True)
    because all content goes through escape_for_html_bubble() and the
    LLM output was already run through sanitize_llm_response().
    """
    cards_html = []
    for sec_key, (icon, label, colour) in CARD_DEFS.items():
        pattern = rf"## {sec_key}\s*(.*?)(?=## [A-Z]|\Z)"
        m = re.search(pattern, insights_text, re.DOTALL | re.IGNORECASE)
        if not m:
            continue
        raw = m.group(1).strip()
        if not raw:
            continue

        # Convert bullet lines to HTML list items (safe — content is sanitized)
        lines = raw.splitlines()
        items_html = ""
        for line in lines:
            clean = line.lstrip("-•* ").strip()
            if clean:
                items_html += f"<li>{escape_for_html_bubble(clean)}</li>"

        body_html = (
            f"<ul style='margin:.25rem 0 0 1rem;padding:0;'>{items_html}</ul>"
            if items_html
            else f"<p style='margin:0;'>{escape_for_html_bubble(raw)}</p>"
        )

        cards_html.append(f"""
<div class="pp-icard {colour}" style="margin-bottom:10px;">
  <div class="pp-icard-header">
    <div class="pp-icard-icon">{icon}</div>
    <span class="pp-icard-label">{escape_for_html_bubble(label)}</span>
  </div>
  <div class="pp-icard-body">{body_html}</div>
</div>""")

    if not cards_html:
        return ""

    # Pair cards into 2-col rows
    rows_html = ""
    for i in range(0, len(cards_html), 2):
        pair = cards_html[i: i + 2]
        cols = "".join(f'<div style="flex:1;min-width:0;">{c}</div>' for c in pair)
        rows_html += (
            f'<div style="display:flex;gap:10px;flex-wrap:wrap;">{cols}</div>'
        )

    intro = (
        '<p style="font-size:.85rem;color:#64748B;margin:0 0 .75rem;">'
        "Here's a structured summary of your policy. "
        "Ask me anything about specific coverage, exclusions, or claims."
        "</p>"
    )
    return intro + rows_html


def _inject_insight_cards() -> None:
    """
    Build the insight card message and prepend it to chat_history as
    the first assistant message (index 0).  Idempotent — sets
    insights_injected=True so it only fires once per document load.
    """
    if st.session_state.insights_injected:
        return
    if not st.session_state.policy_insights:
        return

    cards_html = _build_insight_cards_html(st.session_state.policy_insights)
    if cards_html:
        # Insert at index 0 so it's always the opening assistant message
        st.session_state.chat_history.insert(0, {
            "role": "assistant",
            "content": cards_html,
            "is_html": True,   # flag: render with unsafe_allow_html
        })
    st.session_state.insights_injected = True


# ─── Question handler ─────────────────────────────────────────────────────────

def _handle_question(question: str) -> None:
    """
    Sole writer of chat_history (except _inject_insight_cards).
    user msg → RAG retrieve → Groq LLM → assistant msg.
    Idempotency guard prevents duplicate LLM calls.
    """
    question = question.strip()
    if not question:
        return

    history = st.session_state.chat_history

    # Guard: identical consecutive question
    user_entries = [m for m in history if m["role"] == "user"]
    if user_entries and user_entries[-1]["content"] == question:
        return

    history.append({"role": "user", "content": question, "is_html": False})

    with st.spinner("🔍 Searching your policy…"):
        context = retrieve_context(st.session_state.vector_store, question)

    with st.spinner("🤖 Insurio is thinking…"):
        result = generate_answer(
            question=question,
            context=context,
            chat_history=[m for m in history[:-1] if not m.get("is_html")],
        )

    if result["error"]:
        history.pop()
        st.error(f"❌ {result['error']}")
    else:
        history.append({
            "role": "assistant",
            "content": sanitize_llm_response(result["answer"]),
            "is_html": False,
        })


# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    st.markdown("---")

    if bool(get_api_key()):
        st.markdown(
            '<div class="pp-info">✅ <strong>GROQ_API_KEY</strong> '
            'loaded from <code>.env</code></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="pp-warn">⚠️ <strong>GROQ_API_KEY</strong> not found.<br>'
            'Create <code>.env</code>: <code>GROQ_API_KEY=gsk_…</code></div>',
            unsafe_allow_html=True,
        )
        st.markdown("[Get a free key →](https://console.groq.com)")

    st.markdown("---")
    st.markdown("**🎙️ Voice Input**")
    _vs = get_voice_status()
    if _vs == "available":
        st.success("Microphone ready", icon="🎙️")
    elif _vs == "partial":
        st.warning("Install pyaudio for voice")
        st.code("pip install pyaudio")
    else:
        st.caption("Voice unavailable")
        st.code("pip install SpeechRecognition pyaudio")

    st.markdown("---")
    if st.session_state.vector_store is not None:
        st.markdown("**📄 Loaded Policy**")
        st.caption(st.session_state.policy_name or "—")
        st.caption(
            f"{st.session_state.policy_pages} pages · "
            f"{st.session_state.policy_chunks} chunks · "
            f"{st.session_state.retrieval_method.title()} retrieval"
        )
        if st.button("🗑️ Clear & Upload New", use_container_width=True):
            for k in ["vector_store", "policy_text", "policy_name", "policy_insights"]:
                st.session_state[k] = None
            st.session_state.policy_pages      = 0
            st.session_state.policy_chunks     = 0
            st.session_state.chat_history      = []
            st.session_state.voice_prefill     = ""
            st.session_state.retrieval_method  = "keyword"
            st.session_state.insights_injected = False
            st.rerun()

    st.markdown("---")
    st.caption("Insurio v4.0 · Powered by Groq + LLaMA 3")


# ══════════════════════════════════════════════════════════════════════════════
#  STICKY HEADER — rendered once, always visible
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state.vector_store is None:
    # Landing header — no doc chip
    st.markdown("""
    <div class="pp-header">
      <div class="pp-header-left">
        <div class="pp-logo">🛡️</div>
        <div class="pp-brand">
          <div class="pp-brand-name">Insurio</div>
          <div class="pp-brand-sub">AI Insurance Policy Intelligence</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
else:
    # Workspace header — show doc chip
    policy_name_safe = escape_for_html_bubble(st.session_state.policy_name or "")
    st.markdown(f"""
    <div class="pp-header">
      <div class="pp-header-left">
        <div class="pp-logo">🛡️</div>
        <div class="pp-brand">
          <div class="pp-brand-name">Insurio <em></em></div>
          <div class="pp-brand-sub">AI Insurance Policy Intelligence</div>
        </div>
      </div>
      <div class="pp-doc-chip">
        <span class="pp-doc-chip-dot"></span>
        {policy_name_safe}
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Slim metadata bar beneath the header
    st.markdown(f"""
    <div class="pp-meta-bar">
      <span>✅ Policy loaded</span>
      <span class="pp-divider-dot">·</span>
      <span class="pp-pill">📄 {st.session_state.policy_pages} pages</span>
      <span class="pp-pill">🧩 {st.session_state.policy_chunks} chunks</span>
      <span class="pp-pill">🔍 {st.session_state.retrieval_method.title()}</span>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  LANDING PAGE  (no document loaded)
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state.vector_store is None:

    # ── Hero section ───────────────────────────────────────────────────────
    _, hero_col, _ = st.columns([1, 3, 1])
    with hero_col:
        st.markdown("""
        <div class="pp-hero">
          <div class="pp-hero-badge">🛡️ &nbsp; AI Document Assistant</div>
          <h1 class="pp-hero-title">
            Ask anything about<br>your insurance policy
          </h1>
          <p class="pp-hero-sub">
            Upload your PDF, and Insurio AI will instantly analyse
            coverage, exclusions, waiting periods — and answer your
            questions in plain English.
          </p>
        </div>
        """, unsafe_allow_html=True)

    # ── Upload drop zone ────────────────────────────────────────────────────
    _, upload_col, _ = st.columns([1, 2, 1])
    with upload_col:
        st.markdown("""
        <div class="pp-dropzone">
          <span class="pp-dropzone-icon">📋</span>
          <div class="pp-dropzone-title">Drop your insurance policy here</div>
          <div class="pp-dropzone-hint">PDF · Health, life, auto, home &amp; more</div>
        </div>
        """, unsafe_allow_html=True)

        uploaded_file = st.file_uploader(
            "Choose a PDF",
            type=["pdf"],
            label_visibility="collapsed",
            help="Upload any insurance policy in PDF format",
        )

        if uploaded_file is not None:
            if not get_api_key():
                st.markdown(
                    '<div class="pp-warn">⚠️ <strong>GROQ_API_KEY</strong> not found. '
                    'Add it to your <code>.env</code> file and restart.</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="pp-processing">'
                    '⚙️ &nbsp;<strong>Processing document…</strong>'
                    '&nbsp; Extracting text, building knowledge base…'
                    '</div>',
                    unsafe_allow_html=True,
                )
                with st.spinner(""):
                    result = process_document(uploaded_file)

                if result.get("error"):
                    st.markdown(
                        f'<div class="pp-err">❌ {result["error"]}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.session_state.vector_store     = result["vector_store"]
                    st.session_state.policy_text      = result["text"]
                    st.session_state.policy_name      = uploaded_file.name
                    st.session_state.policy_pages     = result["pages"]
                    st.session_state.policy_chunks    = result["chunk_count"]
                    st.session_state.retrieval_method = result["retrieval_method"]

                    with st.spinner("Analysing policy and generating insights…"):
                        ins = generate_policy_insights(result["text"])
                        if ins.get("insights"):
                            st.session_state.policy_insights = ins["insights"]

                    st.rerun()

    # ── Feature trio ────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    _, feat_col, _ = st.columns([1, 4, 1])
    with feat_col:
        f1, f2, f3 = st.columns(3)
        for col, icon, name, desc in [
            (f1, "🔍", "Smart RAG Search",
             "Semantic search surfaces the most relevant clauses instantly"),
            (f2, "💬", "Natural Language Chat",
             "Ask in plain English; get clear, precise answers with citations"),
            (f3, "🎙️", "Voice Queries",
             "Speak your question — Insurio transcribes and responds"),
        ]:
            with col:
                st.markdown(f"""
                <div class="pp-feature">
                  <div class="pp-feature-icon">{icon}</div>
                  <div class="pp-feature-name">{name}</div>
                  <div class="pp-feature-desc">{desc}</div>
                </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  WORKSPACE  (document loaded — conversation-first, no split screen)
# ══════════════════════════════════════════════════════════════════════════════

else:
    # ── Inject insight cards once (as the opening assistant message) ────────
    _inject_insight_cards()

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 1 — RESOLVE USER INPUT
    #
    # st.chat_input() is called at the TOP LEVEL of the else block,
    # directly in the script body — NOT inside any column or container.
    # This is what gives Streamlit full authority over the sticky-bottom
    # placement and guarantees the widget resets to None on every rerun
    # except the one triggered by the user pressing Send.
    #
    # Returns: str  on the single rerun caused by pressing Enter / Send
    #          None on every other rerun (auto-reruns, button clicks, etc.)
    # ─────────────────────────────────────────────────────────────────────────
    user_input = st.chat_input(
        placeholder="Ask your policy anything…",
        key="main_chat_input",
    )

    # Consume voice prefill (read + clear atomically).
    # chat_input always wins; prefill is used only when chat_input is None.
    _prefill = st.session_state.voice_prefill
    if _prefill:
        st.session_state.voice_prefill = ""
        if not user_input:
            user_input = _prefill

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 2 — DISPATCH (before render so history is fully updated)
    # ─────────────────────────────────────────────────────────────────────────
    if user_input:
        if not get_api_key():
            st.error("🔑 **GROQ_API_KEY** not found. Add it to `.env` and restart.")
        else:
            _handle_question(user_input)
            st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 3 — RENDER: single centred conversation column
    #
    # No split layout. All messages appear in a single centred column,
    # max-width 760 px, matching the chat input bar width.
    # The welcome state / suggestion chips appear when history has only the
    # opening insight-card message (or is empty).
    # ─────────────────────────────────────────────────────────────────────────
    _, conv_col, _ = st.columns([1, 3, 1])

    with conv_col:
        # Count user messages to decide whether to show welcome / chips
        user_msg_count = sum(1 for m in st.session_state.chat_history
                             if m["role"] == "user")

        # ── Welcome banner + suggestion chips ─────────────────────────────
        if user_msg_count == 0:
            st.markdown("""
            <div class="pp-welcome">
              <div class="pp-welcome-icon">🤖</div>
              <h3 class="pp-welcome-title">Ready to answer your questions</h3>
              <p class="pp-welcome-sub">
                Your policy has been loaded and indexed. Ask about coverage,
                waiting periods, exclusions, claims — anything.
              </p>
            </div>
            """, unsafe_allow_html=True)

        # ── Message render loop (pure read-only) ──────────────────────────
        # No LLM calls, no state mutations inside this block.
        for msg in st.session_state.chat_history:
            role    = msg["role"]
            content = msg["content"]
            is_html = msg.get("is_html", False)

            if role == "user":
                with st.chat_message("user"):
                    # User text: plain Markdown — escape_for_html_bubble was
                    # applied if it ever reaches an HTML context; here we use
                    # plain st.markdown (no unsafe) so tags render as text.
                    st.markdown(content)
            else:
                with st.chat_message("assistant", avatar="🛡️"):
                    if is_html:
                        # Insight cards — pre-built safe HTML
                        st.markdown(content, unsafe_allow_html=True)
                    else:
                        # Regular LLM response — plain Markdown, sanitized at store time
                        st.markdown(content)

        # ── Suggestion chips (only before first user message) ─────────────
        if user_msg_count == 0:
            SUGGESTIONS = [
                "Is knee replacement surgery covered?",
                "What are the waiting periods?",
                "What are the main exclusions?",
                "How do I file a claim?",
                "Is cataract surgery covered?",
                "What is my annual deductible?",
            ]
            st.markdown('<div class="pp-chips-wrap">', unsafe_allow_html=True)
            chip_cols_1 = st.columns(3)
            chip_cols_2 = st.columns(3)
            for i, col in enumerate(chip_cols_1):
                with col:
                    if st.button(SUGGESTIONS[i], key=f"chip_{i}",
                                 use_container_width=True):
                        st.session_state.voice_prefill = SUGGESTIONS[i]
                        st.rerun()
            for i, col in enumerate(chip_cols_2):
                with col:
                    if st.button(SUGGESTIONS[i + 3], key=f"chip_{i+3}",
                                 use_container_width=True):
                        st.session_state.voice_prefill = SUGGESTIONS[i + 3]
                        st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # ─────────────────────────────────────────────────────────────────────
        # STEP 4 — ACTION ROW  (voice + clear, centred above the input bar)
        #
        # Rendered OUTSIDE st.chat_input() so Streamlit doesn't shift the
        # input bar.  Both buttons write to voice_prefill / clear state and
        # call st.rerun() — the prefill is consumed in STEP 1 on that rerun.
        # ─────────────────────────────────────────────────────────────────────
        st.markdown('<div class="pp-action-row">', unsafe_allow_html=True)
        act_l, act_r = st.columns([1, 1])

        with act_l:
            st.markdown('<div class="pp-voice-wrap">', unsafe_allow_html=True)
            mic_clicked = st.button(
                "🎙️ Voice input",
                help="Click and speak your question",
                key="mic_btn",
                use_container_width=True,
            )
            st.markdown('</div>', unsafe_allow_html=True)

        with act_r:
            if st.session_state.chat_history:
                st.markdown('<div class="pp-clear-wrap">', unsafe_allow_html=True)
                if st.button("🗑️ Clear conversation", key="clear_btn",
                             use_container_width=True):
                    st.session_state.chat_history     = []
                    st.session_state.insights_injected = False
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        if mic_clicked:
            if get_voice_status() == "available":
                with st.spinner("🎙️ Listening… speak now"):
                    vr = transcribe_audio()
                if vr["text"]:
                    st.session_state.voice_prefill = vr["text"]
                    st.rerun()
                else:
                    st.markdown(
                        f'<div class="pp-err">🎙️ {vr["error"]}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    '<div class="pp-warn">🎙️ Voice requires pyaudio. '
                    'Run: <code>pip install pyaudio</code></div>',
                    unsafe_allow_html=True,
                )

        # Footer caption inside the conversation column
        st.markdown("""
        <div class="pp-footer-caption">
          Insurio · Powered by Groq + LLaMA 3 ·
          For informational purposes only ·
          Always verify coverage directly with your insurer.
        </div>
        """, unsafe_allow_html=True)