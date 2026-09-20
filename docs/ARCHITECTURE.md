# AgentIQ - System Architecture

## 1. Overview

AgentIQ is an autonomous multi-agent research and task assistant designed to transform a high-level research goal into a structured, evidence-based final report.

The platform combines:

- Multi-agent orchestration
- LangGraph workflow execution
- Large Language Models
- Retrieval-Augmented Generation (RAG)
- Web research
- Image and video search
- Parallel task execution
- Research caching
- Error recovery and retry
- Evidence deduplication and quality checks
- Authentication and authorization
- React frontend
- FastAPI backend
- PostgreSQL

The overall workflow is:

```text
User Goal
   |
   v
Authentication
   |
   v
React Dashboard
   |
   v
FastAPI API
   |
   v
Research Graph
   |
   v
Planner
   |
   v
Parallel Research
   |- Web Search
   |- RAG
   |- Image Search
   `- Video Search
   |
   v
Evidence Processing
   |
   v
Writer
   |
   v
Critic
   |
   v
Revision
   |
   v
Final Research Report
   |
   v
React Dashboard
```

## 2. High-Level System Architecture

```text
+-------------------+
|       User        |
+---------+---------+
          |
          v
+-------------------+
|  React Frontend   |
| Pages Components  |
| Hooks Services UI |
+---------+---------+
          | HTTP / SSE
          v
+-------------------+
|  FastAPI Backend  |
| Auth Research     |
| Documents Health  |
+---------+---------+
          |
          v
+-------------------+
|  Research Graph   |
|    LangGraph      |
+---------+---------+
          |
    +-----+-----+-----+
    |           |     |
    v           v     v
 Planner   Researcher Writer
    |           |     |
    |     +-----+-----+
    |     |     |     |
    |     v     v     v
    |   Web    RAG  Image/Video
    | Search Search  Search
    |           |
    |           v
    |    Evidence Processing
    |           |
    +-----------v
             Critic
               |
               v
          Final Report
```

## 3. Frontend Architecture

The frontend is implemented with React and Vite.

```text
frontend/
`-- src/
    |-- assets/
    |-- components/
    |-- hooks/
    |-- pages/
    |-- services/
    |-- App.jsx
    |-- App.css
    |-- index.css
    `-- main.jsx
```

The frontend handles authentication, research goal submission, progress display, agent event visualization, final report rendering, evidence presentation, image and video results, API communication, and loading or error states. It communicates with the backend through REST APIs and Server-Sent Events (SSE).

## 4. Backend Architecture

The backend is implemented with FastAPI.

```text
backend/app/
|-- agents/
|-- api/
|   `-- routes/
|-- config/
|-- database/
|-- graph/
|-- llm/
|-- rag/
|-- schemas/
|-- tools/
`-- utils/
```

- `agents/` contains the Planner, Researcher, Writer, Critic, and revision behavior.
- `api/` contains FastAPI route definitions for authentication, documents, health, and research.
- `config/` centralizes environment-based settings.
- `database/` handles connectivity and persistence.
- `graph/` contains the LangGraph workflow and state transitions.
- `llm/` contains the LLM client and response handling.
- `rag/` contains document retrieval and RAG functionality.
- `schemas/` contains Pydantic request and response models.
- `tools/` contains external research tools such as web search.
- `utils/` contains caching, retry handling, security, prompt protection, evidence processing, and error handling.

## 5. Research Workflow

The core workflow is a multi-stage pipeline:

```text
Research Goal
     |
     v
  Planner
     |
     v
Research Tasks
     |
  +--+----------+--+
  |  |          |  |
  v  v          v  v
 Web RAG      Image Video
Search Search  Search Search
  |  |          |  |
  +--+----------+--+
     |
     v
Evidence Set
     |
     v
Researcher -> Writer -> Critic -> Revision -> Final Report
```

### Planner Agent

The Planner converts a high-level goal into smaller research tasks. For example, a goal about the impact of generative AI on developer productivity can be decomposed into productivity measurements, usage studies, benefits, limitations, and comparisons of major findings.

### Researcher Agent

The Researcher gathers relevant information, source references, evidence, metadata, images, and videos from web search, RAG, and multimedia sources.

### Parallel Research

Independent research operations can execute concurrently. Concurrency is limited to avoid uncontrolled external API usage while reducing unnecessary waiting between independent searches.

## 6. Retrieval-Augmented Generation

The RAG pipeline uses indexed documents as a research source:

```text
Document -> Loading -> Splitting -> Embeddings -> Vector Store
         -> Similarity Search -> Relevant Context -> LLM -> Output
```

RAG is useful when research should be grounded in provided documents or stored knowledge.

## 7. Web and Multimedia Research

Web research follows this flow:

```text
Research Task -> Query Generation -> Web Search -> Result Collection
              -> Evidence Processing -> Deduplication -> Quality Evaluation
              -> Research Context
```

Image and video search extend the research experience beyond text. Results are normalized alongside textual evidence and exposed to the frontend for presentation.

## 8. Evidence Processing

Raw results are normalized, deduplicated, and checked for evidence quality before reaching the Writer. This reduces duplicate information and improves the context supplied to report generation.

```text
Raw Results -> Normalization -> Deduplication -> Quality Checks
            -> Relevant Evidence -> Writer
```

## 9. Writer, Critic, and Revision

The Writer constructs a report from collected evidence. The Critic evaluates completeness, evidence usage, relevance, logical consistency, missing information, unsupported claims, and overall quality. Critic feedback feeds a revision stage before the final report is returned.

```text
Evidence -> Context Construction -> LLM -> Draft
Draft -> Critic -> Feedback -> Revision -> Improved Report
```

## 10. LLM Architecture and Resilience

```text
Agent -> LLM Client -> Provider -> Model Response
      -> Response Parsing -> Structured Agent Output
```

The centralized LLM client handles provider calls, timeout and API errors, rate-limit retries, concurrency control, request pacing, and structured JSON responses. When a model returns surrounding text around a JSON object, the client can attempt to recover the object before reporting invalid JSON.

## 11. Caching and Error Recovery

Caching avoids repeated research work:

```text
Research Request -> Cache Check
                   |          |
                  HIT        MISS -> Research -> Cache
                   |          |
                   +---- Result
```

Transient external failures are handled with bounded retries and backoff. Persistent failures are converted into consistent application errors so one unavailable provider does not produce an uncontrolled crash.

## 12. Security and Authentication

Security is applied across the request path:

```text
User -> Authentication -> JWT Validation -> Input Validation
     -> Prompt Security -> Agent Workflow -> External Tools
```

Security components include JWT authentication, Argon2 password hashing, input validation, prompt injection protection, environment-based secrets, protected endpoints, and controlled external tool execution. Secrets remain outside source code in environment configuration.

Authentication follows this flow:

```text
Register / Login -> Password Verification -> JWT Access Token
                  -> Protected API -> Authorized Request
```

## 13. Database Architecture

PostgreSQL provides persistent application storage through SQLAlchemy:

```text
FastAPI -> Database Layer -> SQLAlchemy -> PostgreSQL
```


## 14. API Architecture

The API is organized into functional route groups:

```text
FastAPI
  |-- Auth
  |-- Research
  |-- Documents
  `-- Health
```

Important research endpoints include:

```text
POST /api/research
GET  /api/research/{id}
GET  /api/research/{id}/events
GET  /api/research/{id}/stream
```

## 15. Server-Sent Events

The backend publishes research progress events through an SSE stream. The React frontend consumes those events to update the live progress interface without continuously polling the backend.

```text
Backend Research Process -> SSE Stream -> React Frontend -> Live Progress UI
```

## 16. End-to-End Request Flow

1. The user logs in.
2. The user submits a research goal.
3. React sends the API request.
4. FastAPI validates the request.
5. A research task is created.
6. The Planner decomposes the goal.
7. Research tasks execute.
8. Web, RAG, image, and video tools gather evidence.
9. Evidence is deduplicated and evaluated.
10. The Writer generates a draft.
11. The Critic evaluates the draft.
12. Revision improves the output.
13. The final report is stored or returned.
14. The React dashboard displays the result.



```text
  |-- postgres   PostgreSQL 16 with persistent volume
  |-- backend    FastAPI and Uvicorn on port 8000
  `-- frontend   React build served on port 80
```

The backend image installs Python dependencies and CPU-compatible Torch, copies the application, and starts Uvicorn. The frontend image builds the Vite application and serves the generated assets. The backend waits for PostgreSQL health before starting through the Compose dependency condition.

## 18. Operational Checks

Useful verification commands from the repository root are:

```powershell
python -m pytest -q
npm --prefix frontend run build
Invoke-WebRequest http://localhost:8000/api/health
Invoke-WebRequest http://localhost
git diff --check
```

These checks validate backend behavior, frontend compilation, container state, HTTP availability, and whitespace errors before deployment changes are committed.
