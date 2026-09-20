# AgentIQ

**Autonomous Multi-Agent Research & Task Assistant**

AgentIQ is a production-style AI research platform where multiple specialized agents collaborate to research a user-defined topic, gather evidence from multiple sources, generate a structured report, critique the result, and improve the final output.

The system combines **multi-agent orchestration, RAG, web research, multimedia search, LLM resilience, caching, security, authentication, and Vercel/Render deployment** into a single full-stack application.

---

## 🚀 Overview

AgentIQ transforms a research goal into a complete research workflow:

```text
User Research Goal
        ↓
   Planner Agent
        ↓
  Research Pipeline
        ↓
 ┌──────┼──────────┐
 ↓      ↓          ↓
Web    RAG     Multimedia
Search Search   Search
 ↓      ↓          ↓
 └──────┼──────────┘
        ↓
   Researcher Agent
        ↓
    Writer Agent
        ↓
    Critic Agent
        ↓
 Revision / Improvement
        ↓
   Final Research Report
        ↓
    React Dashboard
```

The system is designed to make research **structured, evidence-driven, resilient, and observable** rather than relying on a single LLM response.

---

## ✨ Key Features

### 🤖 Multi-Agent Research

Specialized agents handle different responsibilities:

* **Planner Agent** — breaks the research goal into actionable tasks.
* **Researcher Agent** — gathers relevant information and evidence.
* **Writer Agent** — converts research findings into a structured report.
* **Critic Agent** — evaluates the generated report and identifies weaknesses.
* **Revision Pipeline** — improves the final report based on critique.

### 🔎 Multi-Source Research

AgentIQ can combine information from:

* Web search
* RAG / vector database
* Image search
* Video search
* Uploaded documents
* Multiple research sources in parallel

### 📚 Retrieval-Augmented Generation

The RAG pipeline allows AgentIQ to retrieve relevant information from indexed documents and use that information during research and report generation.

### ⚡ Parallel Research

Independent research tasks can execute concurrently instead of waiting for each task sequentially.

This reduces overall research latency and allows multiple information sources to be processed simultaneously.

### 💾 Research Result Caching

Frequently repeated research operations can use cached results to reduce:

* API calls
* Processing time
* LLM usage
* External service dependency

### 🔄 Error Recovery & Retry

AgentIQ includes retry and recovery mechanisms for transient failures such as:

* External API failures
* Temporary network errors
* LLM failures
* Research tool failures

### 🛡️ Security & Input Protection

The backend includes protection mechanisms for:

* Input validation
* Prompt injection detection
* Authentication
* JWT-based authorization
* Secure password hashing
* Environment-based secrets
* API protection

### 👤 Authentication

Users can:

* Register
* Login
* Receive authentication tokens
* Access protected research functionality

### 🖥️ React Dashboard

The frontend provides an interactive interface for:

* Starting research tasks
* Monitoring research progress
* Viewing generated reports
* Viewing research evidence
* Viewing multimedia results
* Tracking agent activity

### 🚀 Production Deployment

AgentIQ is designed to be deployed using Vercel (Frontend) and Render (Backend):

```text
       GitHub Repository
               │
       ┌───────┴───────┐
       ↓               ↓
┌──────────────┐ ┌──────────────┐
│    Vercel    │ │    Render    │
│ React / Vite │ │   FastAPI    │
│   Frontend   │ │   Backend    │
└──────────────┘ └──────┬───────┘
                        │
                        ↓
                 ┌──────────────┐
                 │    Render    │
                 │  PostgreSQL  │
                 └──────────────┘
```

---

## 🧠 Architecture

```text
                         ┌─────────────────┐
                         │      User       │
                         └────────┬────────┘
                                  │
                                  ↓
                         ┌─────────────────┐
                         │ React Dashboard │
                         └────────┬────────┘
                                  │
                                  ↓
                         ┌─────────────────┐
                         │   FastAPI API   │
                         └────────┬────────┘
                                  │
                                  ↓
                         ┌─────────────────┐
                         │ Research Graph  │
                         │   LangGraph     │
                         └────────┬────────┘
                                  │
                 ┌────────────────┼────────────────┐
                 ↓                ↓                ↓
          ┌────────────┐   ┌────────────┐   ┌────────────┐
          │  Planner   │   │ Researcher │   │   Writer   │
          │   Agent    │   │   Agent    │   │   Agent    │
          └────────────┘   └─────┬──────┘   └─────┬──────┘
                                 │                 │
                   ┌─────────────┼─────────────┐   │
                   ↓             ↓             ↓   │
              ┌────────┐   ┌──────────┐   ┌────────┐
              │  Web   │   │   RAG    │   │ Image/ │
              │ Search │   │ Pipeline │   │ Video  │
              └────────┘   └──────────┘   └────────┘
                                 │
                                 ↓
                         ┌─────────────────┐
                         │  Critic Agent   │
                         └────────┬────────┘
                                  │
                                  ↓
                         ┌─────────────────┐
                         │  Final Report   │
                         └─────────────────┘
```

---

## 🧩 Technology Stack

### Backend

* Python
* FastAPI
* LangChain
* LangGraph
* Pydantic
* SQLAlchemy
* PostgreSQL
* ChromaDB
* Sentence Transformers
* PyTorch
* JWT Authentication
* Argon2 password hashing

### Frontend

* React
* Vite
* JavaScript
* CSS
* REST API integration

### AI / LLM

* LLM APIs
* LangChain
* LangGraph
* RAG
* Embeddings
* Prompt engineering
* Structured LLM output
* LLM fallback and resilience mechanisms

### Infrastructure

* PostgreSQL
* Nginx
* WSL2

---

## 📁 Project Structure

```text
AgentIQ/
│
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── auth.py
│   │   │       ├── documents.py
│   │   │       ├── health.py
│   │   │       └── research.py
│   │   │
│   │   ├── config/
│   │   ├── database/
│   │   ├── graph/
│   │   ├── llm/
│   │   ├── rag/
│   │   ├── schemas/
│   │   ├── tools/
│   │   └── utils/
│   │
│   ├── tests/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── assets/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.jsx
│   │
│
├── data/
└── README.md
```

---

## 🔌 API

Important backend endpoints include:

### Health

```http
GET /api/health
```

Used to verify backend availability.

### Authentication

```http
POST /api/auth/register
POST /api/auth/login
```

### Research

```http
POST /api/research
GET /api/research/{id}
GET /api/research/{id}/events
GET /api/research/{id}/stream
```

The streaming endpoint allows the frontend to receive research progress and agent events.

### Documents

```http
POST /api/documents
```

Used for document ingestion and RAG workflows.

---

## ⚙️ Local Development

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd AgentIQ
```

### 2. Backend setup

Create a virtual environment:

```powershell
cd backend

python -m venv venv
```

Activate it:

```powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

### 3. Environment variables

Create:

```text
backend/.env
```

Configure the required environment variables for:

* Database
* JWT
* LLM provider
* Web search
* Multimedia search
* Application configuration

**Never commit `.env` files or API keys to GitHub.**

### 4. Start backend

```powershell
uvicorn app.main:app --reload
```

Backend:

```text
http://localhost:8000
```

Health endpoint:

```text
http://localhost:8000/api/health
```

---

## 🎨 Frontend Setup

From the project root:

```powershell
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://localhost:5173
```

---

## 🚀 Production Deployment (Vercel + Render)

AgentIQ is configured for seamless deployment to modern cloud platforms.

### 1. Backend (Render)
1. Create a new **PostgreSQL** instance on Render.
2. Create a new **Web Service** on Render, pointing to your GitHub repository.
3. Render will automatically detect the `render.yaml` blueprint.
4. Add the required environment variables (`JWT_SECRET_KEY`, `OPENAI_API_KEY`, etc.) in the Render dashboard.

### 2. Frontend (Vercel)
1. Create a new project on Vercel and import your GitHub repository.
2. Ensure the Framework Preset is set to **Vite**.
3. Add the `VITE_API_URL` environment variable pointing to your Render backend URL (e.g., `https://agentiq-backend.onrender.com/api`).
4. Deploy!


---

## 🧪 Testing

AgentIQ contains an automated backend test suite.

Run:

```powershell
.\backend\venv\Scripts\python.exe -m pytest -q
```

Current project verification:

```text
216 passed
```

Additional validation includes:

* Backend regression testing
* Frontend production build
* PostgreSQL health verification
* Backend health endpoint verification
* Frontend HTTP verification
* Git whitespace validation

Frontend production build:

```powershell
cd frontend
npm run build
```

---

## 🔐 Security

Security-related functionality includes:

* JWT authentication
* Secure password hashing with Argon2
* Environment-based secrets
* Input validation
* Prompt injection protection
* Authentication middleware
* Protected API endpoints
* Production configuration
* Error handling without exposing sensitive information

Secrets should always be supplied through environment variables rather than committed to source control.

---

## ⚡ Performance

AgentIQ includes several performance-oriented components:

* Parallel research execution
* Concurrent web/image/video research
* Research result caching
* Vector-store/embedding caching
* API optimization
* Retry mechanisms
* Reduced redundant research
* Evidence deduplication

These components help reduce unnecessary external API calls and improve research response time.

---

## 📊 Research Quality

AgentIQ includes mechanisms for improving research quality:

### Evidence Collection

Research results are collected from multiple sources.

### Deduplication

Duplicate or highly similar evidence can be identified and reduced.

### Evidence Quality

Research evidence is evaluated before being incorporated into the final workflow.

### Critic Agent

The generated report is reviewed before the final response is produced.

This creates a workflow closer to:

```text
Research
   ↓
Evidence
   ↓
Draft
   ↓
Critique
   ↓
Revision
   ↓
Final Report
```

---

## 🛡️ Reliability

AgentIQ is designed to handle failures instead of allowing a single failed external call to terminate the entire research process.

Reliability features include:

```text
External Failure
      ↓
Retry
      ↓
Fallback
      ↓
Continue Pipeline
      ↓
Generate Result
```

LLM response handling also includes fallback extraction for cases where the model returns structured information in a format that requires additional parsing.

---

## 📈 Project Highlights

AgentIQ demonstrates practical implementation of:

* Multi-agent AI systems
* Agent orchestration
* LangGraph workflows
* RAG
* Vector databases
* LLM integration
* Web research
* Multimedia search
* Parallel processing
* Caching
* Error recovery
* Prompt security
* Authentication
* REST APIs
* Server-sent events
* React dashboards
* PostgreSQL
* Production-style deployment
* Automated testing

---

## 🗺️ Development Progress

The project was developed incrementally through **41 development modules** covering:

```text
Core Architecture
       ↓
Multi-Agent Workflow
       ↓
RAG
       ↓
Web Research
       ↓
Image Search
       ↓
Video Search
       ↓
Parallel Research
       ↓
Caching
       ↓
Performance Optimization
       ↓
Error Recovery
       ↓
Research Quality
       ↓
Security
       ↓
API Optimization
       ↓
Frontend Optimization
       ↓
Authentication
       ↓
LLM Resilience
       ↓
Production Readiness
       ↓
Vercel + Render Deployment
```

---

## 🔮 Future Enhancements

Potential future improvements include:

* Advanced agent memory
* More LLM providers
* Additional research sources
* Research citation verification
* Advanced document formats
* User-specific research history
* Team collaboration
* Cloud deployment
* Observability dashboards
* Advanced evaluation benchmarks
* Automated research quality scoring

---

## 👨‍💻 Author

**Abhijat Patel**

B.Tech Information Technology Student

Interests:

* Artificial Intelligence
* Generative AI
* Full Stack Development
* Data Analytics
* Cloud Computing
* Multi-Agent Systems

---

## ⭐ Project Goal

AgentIQ was built to explore how modern AI systems can combine **LLMs, agents, RAG, external tools, databases, frontend interfaces, and deployment infrastructure** into a complete end-to-end application.

The goal is not simply to generate an answer, but to create a system capable of:

```text
Plan → Research → Retrieve → Analyze → Write → Critique → Improve → Deliver
```

---

## 📄 License

Add an appropriate open-source license before publishing the repository publicly.
