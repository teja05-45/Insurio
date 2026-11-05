# Legacy Streamlit prototype (deprecated)

This directory preserves the original Insurio application for reference. **It is not part of the
running product and is not built by Docker Compose or CI.**

The original was a single-process Streamlit app with all state in `st.session_state`: no accounts,
no database, no API, unvalidated uploads, and unverified "citations". Its engineering audit is in
[`../../docs/audit/INITIAL_AUDIT.md`](../../docs/audit/INITIAL_AUDIT.md).

What was reused in the rebuild:

- PyMuPDF for page-accurate extraction;
- the intent of a lexical fallback (now BM25 inside hybrid retrieval);
- the grounding instruction ("never fabricate", "say when evidence is missing"), strengthened into a
  server-validated contract;
- the insight-card information architecture, now a typed schema with quotes, pages and confidence.

Running it is not supported and its dependencies are kept only for historical completeness:

```bash
pip install -r legacy/streamlit/requirements.txt
streamlit run legacy/streamlit/app.py
```

Use the new stack instead — see [`../../docs/LOCAL_SETUP.md`](../../docs/LOCAL_SETUP.md).
