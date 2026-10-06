# Retrievia 📚🧠

**Retrievia** is an AI-powered **Corrective Retrieval-Augmented Generation (CRAG)** platform that helps students learn from their textbooks, notes, research papers, and previous-year question papers.

Upload your study material, then ask questions, generate summaries, and discover important topics, with answers grounded in your own documents.

---

## ✨ Features

- 📄 **Document Intelligence**: upload PDF, TXT, and Markdown files; they are parsed and indexed automatically
- 🔍 **Question Answering**: ask naturally, e.g. *"Explain deadlock prevention."* or *"Where is Dijkstra's Algorithm discussed in my notes?"*
- 🧠 **Summaries**: chapter-wise summaries, revision notes, and exam guides
- 📊 **Past Paper Analysis**: frequently asked concepts, important chapters, topic trends, and estimated weightage
- 🎯 **Topic Discovery**: finds relevant chapters, sections, and related concepts
- 🌐 **Hybrid Retrieval**: combines your documents with trusted educational resources
- 🔄 **Corrective RAG**: evaluates retrieval quality and corrects weak results to reduce hallucinations

```text
Query → Retrieval → Quality Check → (Corrective Retrieval if needed) → Generation → Grounded Answer
```

---

## 🏗️ Tech Stack

| Layer     | Tools                                                  |
|-----------|--------------------------------------------------------|
| Frontend  | Next.js 15, React, TypeScript, ShadCN UI, Tailwind CSS |
| Backend   | Python, FastAPI, LangChain, LangGraph                  |
| Retrieval | RAG, CRAG, vector embeddings, semantic search          |
| Infra     | REST APIs, Docker, vector database                     |

---

## 📁 Project Structure

```text
Retrievia/
├── backend/        # FastAPI app (entry point: app/main.py)
│   ├── app/
│   └── requirements.txt
├── client/         # Next.js frontend
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.x
- Node.js and npm
- Git

### 1. Clone

```bash
git clone <repository-url>
cd Retrievia
```

### 2. Run the backend

```bash
cd backend
python -m venv venv
```

Activate the virtual environment:

```powershell
# Windows PowerShell
venv\Scripts\Activate.ps1
```

```cmd
:: Windows CMD
venv\Scripts\activate
```

```bash
# macOS / Linux
source venv/bin/activate
```

Install dependencies and start the server:

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000
- Docs: http://127.0.0.1:8000/docs

Keep this terminal running.

### 3. Run the frontend

In a **new terminal**:

```bash
cd client
npm install
npm run dev
```

Open http://localhost:3000.

### 4. Use the app

1. Choose **Notes**, **Textbook**, or **Past Paper** and upload a PDF, TXT, or MD file.
2. **Ask**: enter a question about the material.
3. **Summaries**: pick Revision notes, Chapter-wise, or Exam guide.
4. **Past papers**: analyze repeated questions and important topics.

---

## ⚠️ Troubleshooting

| Problem | Fix |
|---------|-----|
| `Could not import module "main"` | Run from the `backend` folder with `python -m uvicorn app.main:app --reload` (not `uvicorn main:app`). |
| Python dependency errors | Activate the virtual environment, then run `pip install -r requirements.txt`. |
| Frontend dependency errors | In `client`, run `npm install` again, then `npm run dev`. |
| Port 3000 / 8000 in use | Stop the process using it, or run on another port. |

---

## 🔐 Configuration

Keep API keys and secrets in environment variables (e.g. a `.env` file) and add `.env` to `.gitignore`. Never commit credentials.

---

## 🎓 Use Cases

Exam preparation • Revision planning • Topic discovery • Previous-year question analysis • Research assistance • Personalized learning

---

## 🎯 Vision

Retrievia aims to become an AI-native learning companion that turns static educational resources into an interactive, searchable, and personalized knowledge system for students worldwide.

---

## 📄 License

Intended for academic and educational purposes. Add an open-source license if distributing publicly.
