# 🛡️ PolicyPilot AI

**AI Insurance Policy Intelligence Assistant**  
A single-page Streamlit workspace for analyzing insurance documents with RAG + Groq LLM.

---

## Features

| Feature | Description |
|---|---|
| 📋 PDF Upload | Parse any insurance policy PDF |
| 🔍 Smart RAG | Semantic search with embeddings (falls back to keyword) |
| 💬 AI Chat | Natural language Q&A powered by Groq LLaMA 3 |
| 📊 Auto Insights | Coverage summary, exclusions, waiting periods |
| 🎙️ Voice Input | Ask questions by speaking |
| 🧠 Chat Memory | Context-aware conversation history |

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

For voice support:
```bash
# macOS
brew install portaudio && pip install pyaudio

# Ubuntu/Debian
sudo apt-get install portaudio19-dev && pip install pyaudio

# Windows
pip install pipwin && pipwin install pyaudio
```

### 2. Get Groq API Key (free)

Visit [console.groq.com](https://console.groq.com) and create a free account.  
Copy your API key.

### 3. Run the app

```bash
streamlit run app.py
```

### 4. Use PolicyPilot AI

1. Open `http://localhost:8501`
2. Paste your Groq API key in the sidebar
3. Upload an insurance policy PDF
4. Ask questions in the chat panel

---

## Architecture

```
policypilot/
├── app.py                    ← Main Streamlit single-page app
├── requirements.txt
└── modules/
    ├── groq_client.py        ← Groq LLM integration (LLaMA 3, Mixtral)
    ├── rag_pipeline.py       ← PDF parsing, chunking, embeddings, retrieval
    ├── voice_input.py        ← Speech-to-text via SpeechRecognition
    └── styles.py             ← Custom CSS design system
```

## RAG Pipeline

```
PDF Upload
    ↓
Text Extraction (PyMuPDF)
    ↓
Chunking (800 chars, 150 overlap)
    ↓
Embeddings (sentence-transformers: all-MiniLM-L6-v2)
    │  └─ Fallback: TF-IDF keyword search
    ↓
In-memory Vector Store (cosine similarity)
    ↓
Query → Top-K Retrieval → Groq LLaMA 3 → Answer
```

## Sample Questions

- *"Is knee replacement surgery covered?"*
- *"What is the waiting period for cataract surgery?"*
- *"What pre-existing conditions are excluded?"*
- *"How do I file a hospitalization claim?"*
- *"What's the maximum annual coverage limit?"*

---

## LLM Models

Uses **Groq** for ultra-fast inference:
- **Primary**: `llama3-70b-8192`
- **Fallback**: `mixtral-8x7b-32768`

---

*Always verify coverage details directly with your insurance provider.*
