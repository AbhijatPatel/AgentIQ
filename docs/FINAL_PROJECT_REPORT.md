# AgentIQ - Autonomous Multi-Agent Research & Task Assistant

## 1. Project Overview

AgentIQ is an autonomous multi-agent research and task-assistance platform that transforms a user-provided research goal into a structured, evidence-supported final report.

The system combines multi-agent orchestration, large language models, Retrieval-Augmented Generation (RAG), web research, image and video search, parallel execution, caching, evidence-quality analysis, deduplication, retry and recovery, authentication, security controls, a FastAPI backend, a React frontend, PostgreSQL, and Docker deployment.

```text
User Goal
   |
   v
Planner Agent -> Research Tasks -> Parallel Researchers
                                  |-- Web Research
                                  |-- RAG / Documents
                                  |-- Image Search
                                  `-- Video Search
   |
   v
Evidence Processing -> Deduplication -> Quality Analysis
   |
   v
Writer Agent -> Critic Agent -> Revision / Validation -> Final Report
```

## 2. Problem Statement and Objectives

Traditional research requires users to understand a question, decompose it, search many sources, compare evidence, remove duplicates, evaluate quality, write a report, and review the result. AgentIQ automates this workflow through specialized collaborating agents.

Project objectives include:

- Automate complex research workflows.
- Decompose large goals into manageable tasks.
- Execute independent work in parallel.
- Combine web, document, image, and video sources.
- Ground results with RAG and evidence processing.
- Improve quality through deduplication and analysis.
- Cache reusable results and recover from temporary failures.
- Protect inputs and provide authenticated API access.
- Deliver a modern web interface and containerized deployment.
- Maintain reliable testing and production-oriented configuration.

## 3. System Architecture

```text
+----------------------+       HTTP / SSE       +----------------------+
|    React Frontend    | <--------------------> |    FastAPI Backend   |
| UI, results, events  |                        | Auth, research, API |
+----------+-----------+                        +----------+-----------+
           |                                               |
           |                                               v
           |                                      +-------------------+
           |                                      | Research Graph    |
           |                                      | LangGraph         |
           |                                      +---------+---------+
           |                                                |
           |                         +----------------------+----------------+
           |                         |                      |                |
           |                         v                      v                v
           |                    Planner              Researcher          Writer
           |                                               |
           |                               +---------------+---------------+
           |                               |               |               |
           |                               v               v               v
           |                             Web             RAG          Image / Video
           |                             Search         Search           Search
           |                               |               |               |
           |                               +---------------+---------------+
           |                                               |
           |                                               v
           |                                      Evidence Processing
           |                                               |
           |                                               v
           |                                             Critic
           |                                               |
           |                                               v
           |                                         Final Report
           +---------------------------------------------------------------+
```

Detailed component architecture is documented in [ARCHITECTURE.md](ARCHITECTURE.md).

## 4. Core Agents and Research Pipeline

### Planner Agent

The Planner receives a high-level goal and decomposes it into focused tasks such as productivity measurements, usage studies, benefits, risks, and industry adoption.

### Researcher Agent

The Researcher gathers information from web search, RAG, image search, and video search. Independent tasks execute concurrently within configured concurrency limits.

### Writer Agent

The Writer converts the collected goal, context, and evidence into a structured research report. It is designed to use gathered evidence rather than unsupported model-generated claims.

### Critic Agent

The Critic reviews completeness, reasoning, evidence usage, relevance, unsupported conclusions, and missing sections. Feedback can trigger revision before the final result is returned.

```text
Planner -> Research -> Evidence Processing -> Writer -> Critic -> Revision
```

## 5. Retrieval and Research Sources

The RAG pipeline is:

```text
Documents -> Loading -> Text Extraction -> Chunking -> Embeddings
          -> Vector Store -> Similarity Search -> Relevant Context -> LLM
```

Web research follows query generation, search, result collection, content extraction, evidence processing, and quality evaluation. Multimedia research adds image metadata and video previews to the unified research experience.

## 6. Parallelism, Caching, and Quality

Independent research tasks run concurrently to reduce latency while bounded workers prevent uncontrolled external API usage.

```text
Research Request -> Cache Check
                    |       |
                   HIT     MISS -> Research -> Save Cache
                    |       |
                    +--- Result
```

The quality pipeline normalizes raw results, detects duplicates, evaluates evidence quality, and supplies only useful evidence to the Writer. Caching reduces repeated API calls, latency, and computation.

## 7. LLM Resilience and Error Recovery

The centralized LLM client provides model configuration, request execution, response processing, retry and backoff handling, timeout handling, concurrency control, and structured response extraction.

When a model returns JSON surrounded by explanatory text, the client can recover the JSON object instead of failing immediately. External transient failures use bounded retries and graceful error handling.

```text
Operation -> Attempt -> Success -> Continue
                    |
                    `-> Failure -> Retry -> Limit -> Graceful Error
```

## 8. Authentication and Security

The security path is:

```text
User -> Authentication -> JWT Validation -> Input Validation
     -> Prompt Security -> Agent Workflow -> External Tools
```

The platform includes password hashing, JWT access control, input validation, prompt-injection protection, unsafe-input filtering, protected endpoints, environment-based secrets, and errors that avoid unnecessary sensitive information. Passwords are never stored as plain text.

## 9. API and Live Progress

The FastAPI backend exposes functional route groups for authentication, research, documents, and health. The research flow creates a job, runs background processing, and exposes status and event information.

Representative endpoints include:

```text
POST /api/research
GET  /api/research/{id}
GET  /api/research/{id}/events
GET  /api/research/{id}/stream
GET  /api/health
```

Server-Sent Events allow the React frontend to receive live progress updates without continuous polling.

## 10. Frontend and Database

The React/Vite frontend provides authentication UI, research requests, progress display, report rendering, evidence presentation, multimedia results, loading states, error states, and responsive interaction.

```text
frontend/src/
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

PostgreSQL provides persistent application data through the database layer and SQLAlchemy. Docker Compose provides the database with a persistent volume and readiness health check.

## 11. Docker Deployment

AgentIQ uses Docker Compose with three services:

```text
Frontend (Nginx, :80)
          |
          v
Backend (FastAPI / Uvicorn, :8000)
          |
          v
PostgreSQL (:5432, persistent volume)
```

The backend image installs application dependencies and CPU-compatible Torch, copies the application, and starts Uvicorn. The frontend image builds the Vite application and serves the production assets. Compose waits for PostgreSQL readiness before starting dependent services.

Typical deployment flow:

```text
Configure Environment -> Build Images -> Start Compose
                      -> PostgreSQL -> Backend -> Frontend
                      -> Health Verification
```

## 12. Production Readiness

Production-oriented improvements include environment configuration, Docker deployment, health monitoring, secure password hashing, JWT authentication, input protection, retry mechanisms, structured errors, API optimization, frontend production builds, and service health verification.

## 13. Testing and Verification

The project includes tests for authentication, API behavior, research workflow, agents, RAG, web and multimedia search, caching, retries, deduplication, evidence quality, security, LLM resilience, and integration behavior.

Final verification results:

```text
Backend regression       -> 216 tests passed
Frontend production build -> Successful
Docker services          -> Running
PostgreSQL               -> Healthy
Backend health           -> HTTP 200, {"status":"ok"}
Frontend health          -> HTTP 200
git diff --check          -> Passed
```

## 14. Project Structure

```text
AgentIQ/
|-- backend/
|   |-- app/
|   |   |-- agents/
|   |   |-- api/
|   |   |-- config/
|   |   |-- database/
|   |   |-- graph/
|   |   |-- llm/
|   |   |-- rag/
|   |   |-- schemas/
|   |   |-- tools/
|   |   `-- utils/
|   |-- tests/
|   |-- Dockerfile
|   |-- requirements.txt
|   `-- .dockerignore
|-- frontend/
|   |-- src/
|   |-- Dockerfile
|   `-- .dockerignore
|-- data/
|-- docs/
|   |-- ARCHITECTURE.md
|   `-- FINAL_PROJECT_REPORT.md
|-- docker-compose.yml
|-- README.md
`-- pytest.ini
```

## 15. Development Progress

AgentIQ was developed incrementally through 41 major modules covering foundation, agent architecture, research, RAG, web and multimedia search, parallelism, caching, performance, retries, quality analysis, security, authentication, integration, production readiness, Docker deployment, and documentation.

Key technical capabilities include multi-agent research, planning, parallel tasks, RAG, vector retrieval, web and multimedia search, evidence processing, deduplication, quality analysis, caching, retry and recovery, LLM fallback handling, JWT authentication, prompt security, SSE events, PostgreSQL persistence, Docker deployment, and automated testing.

## 16. Future Enhancements

Potential future work includes advanced agent memory, source ranking and citation generation, research history, user research libraries, additional LLM providers, distributed task queues, cloud and Kubernetes deployment, role-based access control, analytics, PDF/DOCX export, collaborative workspaces, more multimedia providers, credibility scoring, and advanced planning strategies.

## 17. Final Project Status

**AgentIQ status: Completed**

```text
Core architecture          [x]
Multi-agent workflow       [x]
Research pipeline          [x]
RAG and vector retrieval   [x]
Web/image/video research  [x]
Parallel research          [x]
Caching                    [x]
Performance optimization  [x]
Retry and recovery         [x]
Research quality           [x]
Deduplication              [x]
Security and authentication [x]
API and frontend            [x]
LLM resilience              [x]
Production readiness       [x]
Docker deployment           [x]
Automated testing           [x]
README documentation        [x]
Architecture documentation  [x]
Final project report       [x]
```

## 18. Conclusion

AgentIQ demonstrates how multi-agent orchestration, RAG, web research, multimedia search, evidence processing, LLMs, authentication, security, caching, parallel execution, automated testing, and Docker deployment can be combined into a reliable, modular, deployable full-stack AI application.

The development process emphasized incremental implementation, continuous verification, performance improvements, and production-oriented engineering rather than a simple LLM chatbot.

## Author

**Abhijat Patel**  
B.Tech Information Technology Student

Interests include artificial intelligence, generative AI, full-stack development, data analytics, cloud computing, backend engineering, and multi-agent systems.
