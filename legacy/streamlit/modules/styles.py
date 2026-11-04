"""
PolicyPilot AI — Design System v4.0
────────────────────────────────────
Aesthetic direction: "Refined Utility"
Inspired by Linear, Perplexity, and Clerk.
Font pairing: Instrument Serif (display) + Plus Jakarta Sans (body)
Color: Cool slate-white base, electric indigo accent, warm amber for AI voice.
"""

CUSTOM_CSS = """
<style>

/* ══════════════════════════════════════════════════════════════════
   GOOGLE FONTS
══════════════════════════════════════════════════════════════════ */
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

/* ══════════════════════════════════════════════════════════════════
   DESIGN TOKENS
══════════════════════════════════════════════════════════════════ */
:root {
  /* Palette */
  --bg:            #F8FAFC;
  --bg-alt:        #F1F5F9;
  --surface:       #FFFFFF;
  --surface-hover: #F8FAFC;
  --border:        #E2E8F0;
  --border-light:  #F1F5F9;

  /* Text */
  --text-primary:  #0F172A;
  --text-body:     #334155;
  --text-muted:    #64748B;
  --text-faint:    #94A3B8;
  --text-inverse:  #FFFFFF;

  /* Brand — electric indigo */
  --brand:         #4F46E5;
  --brand-dark:    #3730A3;
  --brand-mid:     #6366F1;
  --brand-light:   #EEF2FF;
  --brand-border:  #C7D2FE;

  /* Semantic */
  --emerald:       #059669;
  --emerald-bg:    #ECFDF5;
  --emerald-border:#6EE7B7;
  --amber:         #D97706;
  --amber-bg:      #FFFBEB;
  --amber-border:  #FCD34D;
  --rose:          #E11D48;
  --rose-bg:       #FFF1F2;
  --rose-border:   #FECDD3;

  /* Insight card accents */
  --card-blue:     #2563EB;
  --card-blue-bg:  #EFF6FF;
  --card-violet:   #7C3AED;
  --card-violet-bg:#F5F3FF;
  --card-rose:     #BE185D;
  --card-rose-bg:  #FDF2F8;
  --card-amber:    #B45309;
  --card-amber-bg: #FFFBEB;
  --card-teal:     #0D9488;
  --card-teal-bg:  #F0FDFA;

  /* Shadows */
  --shadow-xs:  0 1px 2px rgba(15,23,42,0.04);
  --shadow-sm:  0 1px 3px rgba(15,23,42,0.06), 0 1px 2px rgba(15,23,42,0.04);
  --shadow-md:  0 4px 6px rgba(15,23,42,0.05), 0 2px 4px rgba(15,23,42,0.04);
  --shadow-lg:  0 10px 15px rgba(15,23,42,0.06), 0 4px 6px rgba(15,23,42,0.04);
  --shadow-xl:  0 20px 25px rgba(15,23,42,0.08), 0 8px 10px rgba(15,23,42,0.04);
  --shadow-brand: 0 4px 14px rgba(79,70,229,0.20);

  /* Radii */
  --r-xs: 4px;
  --r-sm: 8px;
  --r-md: 12px;
  --r-lg: 16px;
  --r-xl: 20px;
  --r-2xl:24px;
  --r-full: 9999px;

  /* Transitions */
  --t-fast:  0.12s ease;
  --t-med:   0.22s ease;
  --t-slow:  0.35s ease;

  /* Layout */
  --chat-max-width: 760px;
  --header-height:  72px;
}

/* ══════════════════════════════════════════════════════════════════
   GLOBAL RESET
══════════════════════════════════════════════════════════════════ */
*, *::before, *::after { box-sizing: border-box; }

html, body, .stApp {
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
  background: var(--bg) !important;
  color: var(--text-body) !important;
  -webkit-font-smoothing: antialiased !important;
  -moz-osx-font-smoothing: grayscale !important;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header,
.stDeployButton,
[data-testid="stToolbar"],
[data-testid="stDecoration"] { display: none !important; }

/* Page container — centered, generous bottom pad for input bar */
.block-container {
  padding: 0 !important;
  max-width: 100% !important;
  margin: 0 !important;
}

/* Headings use display serif */
h1, h2, h3, h4 {
  font-family: 'Instrument Serif', Georgia, serif !important;
  color: var(--text-primary) !important;
  letter-spacing: -0.02em !important;
  font-weight: 400 !important;
}

/* Thin scrollbars everywhere */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 99px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-faint); }

/* Spinner */
.stSpinner > div {
  border-color: var(--brand) transparent transparent transparent !important;
}

/* ══════════════════════════════════════════════════════════════════
   OUTER WRAPPER  — full-height flex column
══════════════════════════════════════════════════════════════════ */
.pp-app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--bg);
}

/* ══════════════════════════════════════════════════════════════════
   HEADER
══════════════════════════════════════════════════════════════════ */
.pp-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(248,250,252,0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border);
  padding: 0 2rem;
  height: var(--header-height);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.pp-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.pp-logo {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, var(--brand), var(--brand-mid));
  border-radius: var(--r-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  box-shadow: var(--shadow-brand);
  flex-shrink: 0;
}

.pp-brand {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.pp-brand-name {
  font-family: 'Instrument Serif', serif !important;
  font-size: 1.2rem !important;
  font-weight: 400 !important;
  color: var(--text-primary) !important;
  letter-spacing: -0.02em !important;
  line-height: 1 !important;
  margin: 0 !important;
}

.pp-brand-name em {
  color: var(--brand);
  font-style: italic;
}

.pp-brand-sub {
  font-size: 0.7rem !important;
  color: var(--text-faint) !important;
  font-weight: 400 !important;
  letter-spacing: 0.01em !important;
  margin: 0 !important;
}

/* Status chip in header */
.pp-doc-chip {
  display: flex;
  align-items: center;
  gap: 7px;
  background: var(--emerald-bg);
  border: 1px solid var(--emerald-border);
  border-radius: var(--r-full);
  padding: 5px 12px 5px 8px;
  font-size: 0.75rem;
  color: var(--emerald);
  font-weight: 500;
}

.pp-doc-chip-dot {
  width: 6px;
  height: 6px;
  background: var(--emerald);
  border-radius: 50%;
  animation: pulse-dot 2.5s ease infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%       { opacity: 0.55; transform: scale(0.75); }
}

/* ══════════════════════════════════════════════════════════════════
   LANDING PAGE HERO
══════════════════════════════════════════════════════════════════ */
.pp-hero {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 5rem 1.5rem 3rem;
  text-align: center;
  max-width: var(--chat-max-width);
  margin: 0 auto;
  width: 100%;
}

.pp-hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--brand-light);
  color: var(--brand);
  border: 1px solid var(--brand-border);
  border-radius: var(--r-full);
  padding: 5px 14px;
  font-size: 0.71rem;
  font-weight: 600;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  margin-bottom: 1.5rem;
}

.pp-hero-title {
  font-family: 'Instrument Serif', serif !important;
  font-size: 3.25rem !important;
  font-weight: 400 !important;
  color: var(--text-primary) !important;
  line-height: 1.12 !important;
  letter-spacing: -0.03em !important;
  margin: 0 0 1rem !important;
}

.pp-hero-title em {
  color: var(--brand);
  font-style: italic;
}

.pp-hero-sub {
  font-size: 1.05rem !important;
  color: var(--text-muted) !important;
  font-weight: 400 !important;
  line-height: 1.6 !important;
  margin: 0 0 2.5rem !important;
  max-width: 480px;
}

/* ── Upload drop zone ── */
.pp-dropzone {
  width: 100%;
  background: var(--surface);
  border: 2px dashed var(--border);
  border-radius: var(--r-xl);
  padding: 2.75rem 2rem;
  transition: border-color var(--t-med), background var(--t-med), box-shadow var(--t-med);
  box-shadow: var(--shadow-sm);
  margin-bottom: 1.5rem;
}

.pp-dropzone:hover {
  border-color: var(--brand);
  background: var(--brand-light);
  box-shadow: 0 0 0 4px rgba(79,70,229,0.06), var(--shadow-md);
}

.pp-dropzone-icon {
  font-size: 2.25rem;
  margin-bottom: 12px;
  display: block;
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.08));
}

.pp-dropzone-title {
  font-family: 'Instrument Serif', serif;
  font-size: 1.2rem;
  color: var(--text-primary);
  margin-bottom: 5px;
}

.pp-dropzone-hint {
  font-size: 0.82rem;
  color: var(--text-faint);
}

/* Override Streamlit file uploader inside drop zone */
.stFileUploader > div   { background: transparent !important; border: none !important; }
.stFileUploader label   { font-size: 0.875rem !important; color: var(--text-muted) !important; }
[data-testid="stFileUploaderDropzone"] {
  background: transparent !important;
  border: none !important;
}

/* Processing bar */
.pp-processing {
  display: flex;
  align-items: center;
  gap: 10px;
  background: linear-gradient(135deg, var(--brand-light), #E0E7FF);
  border: 1px solid var(--brand-border);
  border-radius: var(--r-md);
  padding: 0.75rem 1.1rem;
  font-size: 0.875rem;
  color: var(--brand-dark);
  margin: 0.75rem 0;
  font-weight: 500;
}

/* Feature trio */
.pp-features {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  width: 100%;
  margin-top: 1.5rem;
}

.pp-feature {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: 1.1rem 0.9rem;
  text-align: center;
  box-shadow: var(--shadow-xs);
  transition: box-shadow var(--t-med), transform var(--t-med), border-color var(--t-med);
}

.pp-feature:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
  border-color: var(--brand-border);
}

.pp-feature-icon { font-size: 1.4rem; margin-bottom: 7px; }
.pp-feature-name {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 3px;
}
.pp-feature-desc {
  font-size: 0.73rem;
  color: var(--text-muted);
  line-height: 1.4;
}

/* ══════════════════════════════════════════════════════════════════
   CONVERSATION PAGE — full-width single-column
══════════════════════════════════════════════════════════════════ */
.pp-conversation {
  flex: 1;
  display: flex;
  flex-direction: column;
  max-width: var(--chat-max-width);
  margin: 0 auto;
  width: 100%;
  padding: 1.5rem 1rem 9rem;   /* bottom pad = chat bar height + breathing room */
}

/* ── Welcome state (inside conversation area, no history yet) ── */
.pp-welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 3rem 1rem 1.5rem;
}

.pp-welcome-icon {
  width: 56px;
  height: 56px;
  background: linear-gradient(135deg, var(--brand-light), #E0E7FF);
  border: 1px solid var(--brand-border);
  border-radius: var(--r-xl);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.6rem;
  margin-bottom: 14px;
  box-shadow: var(--shadow-brand);
}

.pp-welcome-title {
  font-family: 'Instrument Serif', serif !important;
  font-size: 1.4rem !important;
  color: var(--text-primary) !important;
  margin: 0 0 6px !important;
}

.pp-welcome-sub {
  font-size: 0.85rem !important;
  color: var(--text-muted) !important;
  margin: 0 0 1.5rem !important;
  line-height: 1.55 !important;
}

/* ── Suggestion chips ── */
.pp-chips-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  justify-content: center;
  margin-top: 0.25rem;
}

/* Chip buttons — scoped so they don't override other buttons */
.pp-chips-wrap .stButton > button {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r-full) !important;
  color: var(--text-body) !important;
  font-size: 0.78rem !important;
  font-weight: 500 !important;
  padding: 6px 14px !important;
  transition: all var(--t-fast) !important;
  box-shadow: var(--shadow-xs) !important;
  white-space: nowrap !important;
}
.pp-chips-wrap .stButton > button:hover {
  border-color: var(--brand) !important;
  color: var(--brand) !important;
  background: var(--brand-light) !important;
  box-shadow: 0 0 0 3px rgba(79,70,229,0.08) !important;
}

/* ══════════════════════════════════════════════════════════════════
   CHAT MESSAGES — st.chat_message() overrides
══════════════════════════════════════════════════════════════════ */

/* Remove Streamlit's default avatar border and give messages room */
[data-testid="stChatMessage"] {
  padding: 0.2rem 0 !important;
  gap: 10px !important;
}

/* Avatar circles */
[data-testid="stChatMessage"] [data-testid="chatAvatarIcon-user"] {
  background: var(--brand-light) !important;
  color: var(--brand) !important;
  border: 1.5px solid var(--brand-border) !important;
  width: 32px !important;
  height: 32px !important;
  border-radius: var(--r-sm) !important;
  font-size: 0.85rem !important;
}

[data-testid="stChatMessage"] [data-testid="chatAvatarIcon-assistant"] {
  background: linear-gradient(135deg, var(--brand), var(--brand-mid)) !important;
  color: white !important;
  border: none !important;
  width: 32px !important;
  height: 32px !important;
  border-radius: var(--r-sm) !important;
  font-size: 0.85rem !important;
  box-shadow: var(--shadow-brand) !important;
}

/* Message content area */
[data-testid="stChatMessageContent"] {
  font-size: 0.9rem !important;
  line-height: 1.7 !important;
  color: var(--text-body) !important;
}

[data-testid="stChatMessageContent"] p    { margin: 0 0 0.5rem !important; }
[data-testid="stChatMessageContent"] p:last-child { margin-bottom: 0 !important; }
[data-testid="stChatMessageContent"] ul,
[data-testid="stChatMessageContent"] ol  { margin: 0.4rem 0 0.5rem 1.1rem !important; padding: 0 !important; }
[data-testid="stChatMessageContent"] li  { margin-bottom: 3px !important; }
[data-testid="stChatMessageContent"] strong { color: var(--text-primary) !important; font-weight: 600 !important; }
[data-testid="stChatMessageContent"] code {
  background: var(--bg-alt) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r-xs) !important;
  padding: 1px 5px !important;
  font-size: 0.82rem !important;
}
[data-testid="stChatMessageContent"] h2,
[data-testid="stChatMessageContent"] h3 {
  font-size: 0.95rem !important;
  margin: 0.8rem 0 0.3rem !important;
}

/* ══════════════════════════════════════════════════════════════════
   INLINE INSIGHT CARDS  (inside assistant messages)
   Rendered via st.markdown with class="pp-icard-*"
══════════════════════════════════════════════════════════════════ */
.pp-icard {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: 1rem 1.1rem;
  margin: 0.75rem 0;
  box-shadow: var(--shadow-sm);
  animation: card-in 0.3s ease;
}

@keyframes card-in {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}

.pp-icard-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 0.7rem;
  padding-bottom: 0.6rem;
  border-bottom: 1px solid var(--border-light);
}

.pp-icard-icon {
  width: 26px; height: 26px;
  border-radius: var(--r-xs);
  display: flex; align-items: center; justify-content: center;
  font-size: 0.8rem;
  flex-shrink: 0;
}

.pp-icard-label {
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
}

/* Colour variants */
.pp-icard.blue   { border-left: 3px solid var(--card-blue);   }
.pp-icard.violet { border-left: 3px solid var(--card-violet); }
.pp-icard.rose   { border-left: 3px solid var(--card-rose);   }
.pp-icard.amber  { border-left: 3px solid var(--card-amber);  }
.pp-icard.teal   { border-left: 3px solid var(--card-teal);   }

.pp-icard.blue   .pp-icard-icon  { background: var(--card-blue-bg);   }
.pp-icard.violet .pp-icard-icon  { background: var(--card-violet-bg); }
.pp-icard.rose   .pp-icard-icon  { background: var(--card-rose-bg);   }
.pp-icard.amber  .pp-icard-icon  { background: var(--card-amber-bg);  }
.pp-icard.teal   .pp-icard-icon  { background: var(--card-teal-bg);   }

.pp-icard.blue   .pp-icard-label { color: var(--card-blue);   }
.pp-icard.violet .pp-icard-label { color: var(--card-violet); }
.pp-icard.rose   .pp-icard-label { color: var(--card-rose);   }
.pp-icard.amber  .pp-icard-label { color: var(--card-amber);  }
.pp-icard.teal   .pp-icard-label { color: var(--card-teal);   }

.pp-icard-body {
  font-size: 0.84rem;
  color: var(--text-body);
  line-height: 1.65;
}

.pp-icard-body ul { margin: 0.25rem 0 0 1rem; padding: 0; }
.pp-icard-body li { margin-bottom: 3px; }
.pp-icard-body strong { color: var(--text-primary); font-weight: 600; }

/* Insight cards grid (used after upload for inline analysis) */
.pp-icards-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin: 0.5rem 0 0.25rem;
}

@media (max-width: 600px) {
  .pp-icards-grid { grid-template-columns: 1fr; }
}

/* ══════════════════════════════════════════════════════════════════
   DOCUMENT META BAR  (thin strip below header when doc is loaded)
══════════════════════════════════════════════════════════════════ */
.pp-meta-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 6px 1rem;
  background: var(--emerald-bg);
  border-bottom: 1px solid var(--emerald-border);
  font-size: 0.75rem;
  color: var(--emerald);
  font-weight: 500;
  flex-wrap: wrap;
}

.pp-meta-bar .pp-pill {
  background: var(--surface);
  border: 1px solid var(--emerald-border);
  border-radius: var(--r-full);
  padding: 2px 9px;
  font-size: 0.7rem;
  color: var(--text-muted);
  font-weight: 500;
}

.pp-divider-dot {
  color: var(--emerald-border);
  font-size: 0.6rem;
}

/* ══════════════════════════════════════════════════════════════════
   CHAT INPUT BAR — sticky bottom ChatGPT style
══════════════════════════════════════════════════════════════════ */

/* Streamlit wraps st.chat_input in this element at the bottom of its
   container.  We use position:sticky to keep it pinned. */
[data-testid="stBottom"] {
  position: sticky !important;
  bottom: 0 !important;
  left: 0 !important;
  right: 0 !important;
  background: linear-gradient(to top, var(--bg) 60%, transparent) !important;
  padding: 1rem 1rem 1.25rem !important;
  z-index: 50 !important;
}

/* The pill input itself */
[data-testid="stChatInput"] {
  max-width: var(--chat-max-width) !important;
  margin: 0 auto !important;
  border-radius: var(--r-xl) !important;
  border: 1.5px solid var(--border) !important;
  background: var(--surface) !important;
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 0.9rem !important;
  box-shadow: var(--shadow-lg) !important;
  transition: border-color var(--t-fast), box-shadow var(--t-fast) !important;
}

[data-testid="stChatInput"]:focus-within {
  border-color: var(--brand) !important;
  box-shadow: 0 0 0 4px rgba(79,70,229,0.10), var(--shadow-lg) !important;
}

/* Inner textarea */
[data-testid="stChatInput"] textarea {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 0.9rem !important;
  color: var(--text-primary) !important;
  padding: 0.75rem 0 0.75rem 1rem !important;
}

[data-testid="stChatInput"] textarea::placeholder {
  color: var(--text-faint) !important;
}

/* Send button — indigo filled circle */
[data-testid="stChatInputSubmitButton"] button {
  background: var(--brand) !important;
  border: none !important;
  border-radius: 50% !important;
  color: white !important;
  width: 34px !important;
  height: 34px !important;
  margin-right: 6px !important;
  transition: background var(--t-fast), transform var(--t-fast), box-shadow var(--t-fast) !important;
  box-shadow: var(--shadow-brand) !important;
}

[data-testid="stChatInputSubmitButton"] button:hover {
  background: var(--brand-dark) !important;
  transform: scale(1.06) !important;
  box-shadow: 0 6px 16px rgba(79,70,229,0.30) !important;
}

/* ══════════════════════════════════════════════════════════════════
   ACTION ROW (voice + clear, rendered above the sticky bar)
══════════════════════════════════════════════════════════════════ */
.pp-action-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 0 0 0.5rem;
  max-width: var(--chat-max-width);
  margin: 0 auto;
  width: 100%;
}

/* Voice button */
.pp-voice-wrap .stButton > button {
  background: var(--amber-bg) !important;
  border: 1.5px solid var(--amber-border) !important;
  border-radius: var(--r-full) !important;
  color: var(--amber) !important;
  font-size: 0.8rem !important;
  font-weight: 600 !important;
  padding: 6px 16px !important;
  box-shadow: var(--shadow-xs) !important;
  transition: all var(--t-fast) !important;
}
.pp-voice-wrap .stButton > button:hover {
  background: #FEF3C7 !important;
  border-color: var(--amber) !important;
  box-shadow: 0 0 0 3px rgba(217,119,6,0.10), var(--shadow-sm) !important;
}

/* Clear button */
.pp-clear-wrap .stButton > button {
  background: transparent !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r-full) !important;
  color: var(--text-faint) !important;
  font-size: 0.76rem !important;
  padding: 6px 14px !important;
  box-shadow: none !important;
  transition: all var(--t-fast) !important;
}
.pp-clear-wrap .stButton > button:hover {
  border-color: var(--rose-border) !important;
  color: var(--rose) !important;
  background: var(--rose-bg) !important;
}

/* ══════════════════════════════════════════════════════════════════
   EXPANDERS (insight accordion)
══════════════════════════════════════════════════════════════════ */
[data-testid="stExpander"] {
  border: 1px solid var(--border) !important;
  border-radius: var(--r-md) !important;
  margin-bottom: 5px !important;
  overflow: hidden !important;
  box-shadow: var(--shadow-xs) !important;
}
.streamlit-expanderHeader,
[data-testid="stExpander"] summary {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 0.84rem !important;
  font-weight: 600 !important;
  color: var(--text-primary) !important;
  background: var(--bg-alt) !important;
  padding: 0.6rem 0.9rem !important;
}
[data-testid="stExpanderDetails"] {
  padding: 0.7rem 0.9rem !important;
  background: var(--surface) !important;
  font-size: 0.83rem !important;
}
[data-testid="stExpanderDetails"] p,
[data-testid="stExpanderDetails"] li {
  font-size: 0.83rem !important;
  color: var(--text-body) !important;
  line-height: 1.6 !important;
}

/* ══════════════════════════════════════════════════════════════════
   GENERAL BUTTONS (default pill)
══════════════════════════════════════════════════════════════════ */
.stButton > button {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-weight: 500 !important;
  border-radius: var(--r-full) !important;
  border: 1.5px solid var(--border) !important;
  background: var(--surface) !important;
  color: var(--text-body) !important;
  transition: all var(--t-fast) !important;
  box-shadow: var(--shadow-xs) !important;
  font-size: 0.84rem !important;
}
.stButton > button:hover {
  border-color: var(--brand) !important;
  color: var(--brand) !important;
  background: var(--brand-light) !important;
}

/* ══════════════════════════════════════════════════════════════════
   SIDEBAR
══════════════════════════════════════════════════════════════════ */
[data-testid="stSidebar"] {
  background: var(--surface) !important;
  border-right: 1px solid var(--border) !important;
}

/* ══════════════════════════════════════════════════════════════════
   ALERT / INFO BOXES
══════════════════════════════════════════════════════════════════ */
.pp-info {
  background: var(--brand-light);
  border: 1px solid var(--brand-border);
  border-radius: var(--r-md);
  padding: 0.7rem 0.95rem;
  font-size: 0.84rem;
  color: var(--brand-dark);
  margin: 0.5rem 0;
}
.pp-warn {
  background: var(--amber-bg);
  border: 1px solid var(--amber-border);
  border-radius: var(--r-md);
  padding: 0.7rem 0.95rem;
  font-size: 0.84rem;
  color: #92400E;
  margin: 0.5rem 0;
}
.pp-err {
  background: var(--rose-bg);
  border: 1px solid var(--rose-border);
  border-radius: var(--r-md);
  padding: 0.7rem 0.95rem;
  font-size: 0.84rem;
  color: var(--rose);
  margin: 0.5rem 0;
}

/* ══════════════════════════════════════════════════════════════════
   FOOTER CAPTION
══════════════════════════════════════════════════════════════════ */
.pp-footer-caption {
  text-align: center;
  padding: 0.5rem 0 1rem;
  font-size: 0.7rem;
  color: var(--text-faint);
  line-height: 1.6;
}

/* ══════════════════════════════════════════════════════════════════
   COLUMN GUTTERS
══════════════════════════════════════════════════════════════════ */
[data-testid="column"] { padding: 0 0.35rem !important; }

</style>
"""


def inject_styles() -> None:
    """Inject the full CSS design system."""
    import streamlit as st
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)