# 🛡️ Insurio

### AI Insurance Policy Intelligence Assistant

**Insurio** is an AI-powered insurance policy assistant that helps users understand complex insurance documents instantly. Upload an insurance PDF and ask questions in natural language. Insurio analyzes the document using **Retrieval-Augmented Generation (RAG)** and **Groq LLaMA models** to deliver clear answers about coverage, exclusions, waiting periods, and claims.

Built with **Streamlit, Groq LLMs, semantic search, and speech-to-text**, Insurio transforms lengthy insurance policies into an interactive conversational experience.

---

# 🚀 Features

| Feature | Description |
|------|------|
| 📄 **PDF Policy Upload** | Upload any insurance policy document for analysis |
| 🔍 **RAG-based Document Search** | Retrieves the most relevant policy clauses using semantic embeddings |
| 💬 **Conversational AI** | Ask questions in plain English and receive contextual answers |
| 📊 **Automated Policy Insights** | Extracts key sections like coverage, exclusions, and waiting periods |
| 🎙️ **Voice Query Support** | Ask questions using speech input |
| 🧠 **Conversation Memory** | Maintains chat context for follow-up questions |

---

# ⚡ Quick Start

## 1️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### Voice Input Support

Install PyAudio depending on your OS.

**macOS**

```bash
brew install portaudio
pip install pyaudio
```

**Ubuntu / Debian**

```bash
sudo apt-get install portaudio19-dev
pip install pyaudio
```

**Windows**

```bash
pip install pipwin
pipwin install pyaudio
```

---

## 2️⃣ Get a Groq API Key

Create a free account and generate an API key:

https://console.groq.com

---

## 3️⃣ Add API Key

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_api_key_here
```

---

## 4️⃣ Run the Application

```bash
streamlit run app.py
```

Open your browser:

```
http://localhost:8501
```

---

# 💡 How It Works

1. Upload an insurance policy PDF.
2. Insurio extracts and indexes the document.
3. The RAG pipeline retrieves the most relevant sections.
4. The LLM generates a contextual answer.
5. Responses are presented in a conversational chat interface.

---

# 🧠 Architecture

```
insurio/
│
├── app.py
├── requirements.txt
│
└── modules/
    ├── groq_client.py
    ├── rag_pipeline.py
    ├── voice_input.py
    ├── sanitize.py
    └── styles.py
```

### Module Responsibilities

| Module | Purpose |
|------|------|
| `app.py` | Main Streamlit application and UI |
| `groq_client.py` | Groq LLM integration |
| `rag_pipeline.py` | Document parsing, chunking, embeddings, retrieval |
| `voice_input.py` | Speech-to-text input |
| `sanitize.py` | Sanitizes LLM responses |
| `styles.py` | Custom UI design system |

---

# 🔍 RAG Pipeline

```
PDF Upload
    ↓
Text Extraction (PyMuPDF)
    ↓
Text Chunking
    ↓
Embedding Generation
(sentence-transformers)
    ↓
Vector Search
(cosine similarity)
    ↓
Top-K Retrieval
    ↓
Groq LLaMA Model
    ↓
AI Response
```

Fallback mechanism:

```
Embedding Search
     ↓
If unavailable
     ↓
TF-IDF Keyword Search
```

---

# 💬 Example Questions

You can ask questions such as:

- “Is knee replacement surgery covered?”
- “What are the waiting periods for cataract surgery?”
- “What conditions are excluded from coverage?”
- “How do I file a hospitalization claim?”
- “What is the maximum annual coverage limit?”

---

# 🤖 LLM Models

Insurio uses **Groq’s high-performance inference**.

| Model | Purpose |
|------|------|
| `llama3-70b-8192` | Primary model for policy understanding |
| `mixtral-8x7b-32768` | Fallback model for complex queries |

---

# 🛠️ Tech Stack

- Python
- Streamlit
- Groq LLM
- Sentence Transformers
- PyMuPDF
- SpeechRecognition
- Retrieval-Augmented Generation (RAG)

---

# ⚠️ Disclaimer

Insurio is designed for informational purposes only.  
Always verify policy details directly with your insurance provider.

---

# 📌 Future Improvements

- Multi-document policy comparison  
- Claim eligibility prediction  
- Policy risk scoring  
- Mobile-friendly UI  
- Multi-language support  
