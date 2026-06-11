<p align="center">
  <h1 align="center">⚖️ NyayBot</h1>
  <p align="center"><strong>AI-powered Indian Legal Document Analyser & RTI Assistant</strong></p>
  <p align="center">
    <a href="#features">Features</a> •
    <a href="#architecture">Architecture</a> •
    <a href="#quick-start">Quick Start</a> •
    <a href="#api-reference">API</a> •
    <a href="#tech-stack">Tech Stack</a>
  </p>
</p>

---

## 🎯 What is NyayBot?

NyayBot is an AI-powered legal assistant that helps Indian citizens understand government and legal documents in plain language. Upload any PDF — RTI replies, court notices, land records, tenancy agreements — and get instant:

- **Document classification** with confidence scoring
- **Key facts extraction** tailored to the legal domain
- **Legal reasoning** with Indian statute citations
- **Step-by-step action plan** with deadlines and contacts
- **Draft response letter** ready to send

It also includes a dedicated **RTI Assistant** that evaluates whether your problem qualifies for an RTI application, drafts the application, and provides filing instructions.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📄 **Document Analysis** | Upload PDF → classify → extract facts → legal reasoning → action plan → draft letter |
| 📝 **RTI Assistant** | Describe a problem → assess RTI applicability → draft application → filing instructions |
| 🔄 **Smart Retry** | Low-confidence classifications automatically retry with broader context |
| 🎯 **Domain-Aware** | Specialised analysis for RTI, Tenant Rights, Income Certificates, Land Records, Court Notices, Employment |
| 🛡️ **Safe Parsing** | All LLM outputs parsed safely — malformed responses never crash the system |
| ⚡ **Agentic Architecture** | LangGraph state machines with conditional branching, not simple chains |

---

## 🏗️ Architecture

<p align="center">
  <img src="docs/architecture.png" alt="NyayBot Architecture Diagram" width="700">
</p>

### How it works

1. **User** uploads a PDF or describes a problem via the web frontend
2. **FastAPI** receives the request at `/api/v1/analyze` or `/api/v1/rti`
3. **Services** extract text (PyMuPDF) and delegate to the appropriate agent
4. **LangGraph Agents** run multi-step pipelines with conditional logic:
   - **Document Agent**: classify → [retry if low confidence] → extract → reason → plan → draft
   - **RTI Agent**: assess → [applicable?] → legal basis → draft → filing **OR** alternate remedies
5. **GitHub Models (GPT-4o)** powers all LLM calls via Azure AI inference
6. Results stream back as structured step-by-step analysis

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- A [GitHub Personal Access Token](https://github.com/settings/tokens) with Models access

### Setup

```bash
# Clone the repo
git clone https://github.com/your-username/NyayBot.git
cd NyayBot

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set your GITHUB_TOKEN

# Run the server
python run.py
```

Open **http://localhost:8000** in your browser.

---

## 📡 API Reference

### `POST /api/v1/analyze`

Upload a PDF document for multi-step legal analysis.

**Request:** `multipart/form-data` with `file` field (PDF)

**Response:**
```json
{
  "steps": [
    {
      "step": "1_classify",
      "title": "Document Classification",
      "content": "**Type:** RTI Reply\n**Legal Domain:** RTI\n**Confidence:** 92%",
      "confidence": 92
    }
  ]
}
```

### `POST /api/v1/rti`

Submit a problem description for RTI applicability analysis.

**Request:** `application/json`
```json
{
  "problem": "I want to know how much money was spent on road construction in my ward."
}
```

**Response:**
```json
{
  "steps": [
    {
      "step": "1_assess",
      "title": "RTI Applicability Assessment",
      "content": "**RTI Applicable:** Yes\n**Confidence:** 95%\n**Department:** Municipal Corporation",
      "confidence": 95
    }
  ]
}
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **LLM** | GPT-4o via GitHub Models (Azure AI inference) |
| **Agent Framework** | LangGraph (state machines with conditional edges) |
| **Backend** | FastAPI + Uvicorn |
| **PDF Processing** | PyMuPDF (fitz) |
| **Settings** | Pydantic Settings |
| **Frontend** | Vanilla HTML/CSS/JS |

---

## 📁 Project Structure

```
NyayBot/
├── app/
│   ├── agents/
│   │   ├── base.py              ← shared LLM client, safe parsers
│   │   ├── document_agent.py    ← LangGraph document analysis agent
│   │   ├── rti_agent.py         ← LangGraph RTI assistant agent
│   │   └── prompts/
│   │       ├── document.py      ← document analysis prompts
│   │       └── rti.py           ← RTI assessment prompts
│   ├── api/v1/
│   │   ├── router.py            ← registers all v1 routes
│   │   └── routes/
│   │       ├── document.py      ← POST /api/v1/analyze
│   │       └── rti.py           ← POST /api/v1/rti
│   ├── core/
│   │   ├── config.py            ← Pydantic BaseSettings
│   │   └── middleware.py        ← CORS registration
│   ├── exceptions/
│   │   └── handlers.py          ← structured error handling
│   ├── schemas/
│   │   ├── document.py          ← request/response models
│   │   └── rti.py
│   ├── services/
│   │   ├── document_service.py  ← PDF → agent orchestration
│   │   └── rti_service.py
│   ├── utils/
│   │   └── pdf_extractor.py     ← PDF text extraction
│   └── main.py                  ← FastAPI app init
├── frontend/
│   └── index.html               ← single-page frontend
├── docs/
│   └── architecture.png         ← architecture diagram
├── run.py                       ← single entry point
├── .env.example
└── requirements.txt
```

---

## 📝 License

Built for the Microsoft Hackathon 2026.

---

<p align="center">
  Made with ❤️ for Indian citizens navigating legal bureaucracy
</p>
