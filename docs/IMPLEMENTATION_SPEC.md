# IdeaMate AI — Production-Grade Implementation Specification

**Claude Code Engineering Guide | Architecture | Implementation Roadmap | Testing Standards**

- **Project:** IdeaMate AI – Intelligent Placement Co-Pilot
- **Problem Statement:** PS-06 – Placement Co-Pilot for Students
- **Prototype Reference:** Orbit – AI Career Co-pilot
- **Document Purpose:** Technical implementation instructions for converting the existing prototype into a scalable, secure, production-ready application.

---

## 1. Project Overview

### 1.1 Product Vision

IdeaMate AI is an intelligent, AI-powered placement assistant designed to help students manage their complete job-search and placement preparation journey from a single platform.

The platform should help students:

- Analyze and improve their resumes.
- Discover relevant job opportunities.
- Match jobs with their skills and experience.
- Generate job-specific resumes and cover letters.
- Track job applications and deadlines.
- Practice role-specific mock interviews.
- Identify skill gaps and receive improvement recommendations.
- Maintain personalized career profiles and learning progress.
- Use AI agents to automate repetitive career-related tasks with human approval.

The objective is to build more than a resume-generation tool. IdeaMate AI should function as a personalized career assistant that supports students throughout their placement journey.

### 1.2 Existing Prototype

The existing Orbit prototype is the primary UI and design reference.

Important implementation requirement:

- Claude Code must inspect the existing project before making modifications.
- Preserve the existing UI design and visual identity.
- Retain functional pages, routes, components and interactions.
- Reuse existing components wherever possible.
- Improve the architecture without unnecessarily redesigning the application.
- Replace mock data with real backend integrations incrementally.
- Clearly distinguish demo functionality from production functionality.
- Do not rebuild the entire application from scratch unless technically necessary.

### 1.3 PPT Presentation Alignment

The implementation should support the technical narrative established in the project presentation.

| PPT slide heading | Corresponding implementation |
| --- | --- |
| The Placement Gap – Problem & Opportunity | Career challenges and user requirements |
| Introducing the AI Placement Co-Pilot | Product modules and core functionality |
| Multi-Agent Architecture & Technology Stack | Backend architecture and AI orchestration |
| Autonomous Workflow – From Resume to Placement | End-to-end agent workflows |
| Intelligent Personalization, Memory & Human Approval | Persistent memory and approval mechanisms |
| Prototype, Measurable Impact & Future Scope | Working application, analytics and scalability |

---

## 2. Functional Requirements

The following modules define the expected product functionality.

### 2.1 Resume Intelligence

**Purpose:** Analyze resumes and convert unstructured resume content into structured career information.

**Features:**

- PDF and DOCX resume uploads.
- Resume text extraction.
- Personal information extraction.
- Education and qualification extraction.
- Technical and soft skill identification.
- Work experience analysis.
- Internship and project identification.
- Resume completeness evaluation.
- Strength and weakness identification.
- Missing skill identification.
- Resume improvement recommendations.
- User verification and editing of extracted information.

**Expected output:** A structured, editable career profile.

### 2.2 Intelligent Job Discovery

**Purpose:** Discover relevant job opportunities based on the student's career profile.

**Features:**

- Job search by role and keywords.
- Location-based job discovery.
- Experience-level filtering.
- Technology and skill filtering.
- Remote, hybrid and onsite preferences.
- Job description extraction.
- Job listing normalization.
- Duplicate job detection.
- Job freshness tracking.
- External application links.
- Initial job source: Adzuna API, subject to API availability, access permissions and usage terms.

### 2.3 AI Job Matching

**Purpose:** Evaluate how well a job matches the student's profile.

**Matching factors:**

- Required skill compatibility.
- Relevant technical skills.
- Experience-level compatibility.
- Job title similarity.
- Education requirements.
- Location preferences.
- Relevant project experience.

**Each job should display:**

- Overall match score.
- Matching skills.
- Missing skills.
- Match explanation.
- Recommended preparation areas.

Matching should combine deterministic scoring and semantic similarity rather than relying entirely on an LLM.

### 2.4 AI Resume Tailoring

**Purpose:** Generate a job-specific resume using the student's verified career information.

**Features:**

- Job description analysis.
- Relevant skill selection.
- Project relevance analysis.
- Resume summary customization.
- Experience and project description refinement.
- ATS-friendly formatting.
- Resume preview.
- Editable generated content.
- PDF/DOCX export.
- Version history.

**Critical rule:** Never invent qualifications, experience, skills, employment history, achievements or numerical metrics.
The original uploaded resume must never be overwritten.

### 2.5 Cover Letter and Application Note Generation

**Features:**

- Job-specific cover letter generation.
- Short application note generation.
- Company and role context.
- Editable generated content.
- Copy and download functionality.
- Version management.

### 2.6 Application Tracking

**Application statuses:**

- Saved
- Preparing
- Awaiting Approval
- Submitted
- Interview Scheduled
- Rejected
- Offer Received
- Withdrawn

**Features:**

- Application dashboard.
- Status management.
- Company information.
- Job details.
- Application dates.
- Deadline tracking.
- Personal notes.
- Activity history.
- Follow-up reminders.

### 2.7 AI Mock Interview

**Features:**

- Role-specific interview preparation.
- Technical interview questions.
- HR interview questions.
- Behavioral interview questions.
- Question-by-question practice.
- Answer collection.
- AI answer evaluation.
- Communication feedback.
- Technical knowledge evaluation.
- Weak-area identification.
- Improvement recommendations.
- Interview performance history.

Feedback must be presented as coaching, not as a guaranteed prediction of hiring success.

### 2.8 Skill Gap Analysis

**Features:**

- Identify missing job-related skills.
- Compare existing skills against job requirements.
- Recommend learning priorities.
- Suggest relevant learning resources.
- Track skill improvement.
- Update career profile as the student gains skills.

### 2.9 Personalized Career Memory

The platform should maintain user-approved information such as:

- Career interests.
- Target job roles.
- Preferred locations.
- Verified skills.
- Career goals.
- Application history.
- Interview performance.
- Learning progress.

Users must be able to view, update and delete their stored information.

### 2.10 Human Approval System

Human approval is mandatory before any external action.

**Examples:**

- Submitting a job application.
- Sending an email to a recruiter.
- Uploading a resume to an external platform.
- Sending application-related messages.

The system may prepare these actions automatically, but execution requires explicit user confirmation.

---

## 3. Technology Stack and API Architecture

Use the existing frontend stack wherever possible.
The following is the recommended backend and AI architecture.

| Layer | Technology | Purpose |
| --- | --- | --- |
| Frontend | Existing prototype framework / React | User interface |
| Backend | Python, FastAPI | REST API and business logic |
| Database | PostgreSQL | Persistent application data |
| AI | OpenAI API | LLM-based intelligence |
| Embeddings | OpenAI Embeddings API | Semantic similarity |
| Agent Framework | LangGraph | Multi-agent orchestration |
| Vector Database | ChromaDB | Semantic retrieval |
| Job API | Adzuna API | Job discovery |
| Authentication | Google OAuth 2.0 / OIDC | User authentication |
| Document Processing | PyMuPDF, python-docx | PDF/DOCX extraction |
| Background Jobs | Redis + worker framework | Async processing |
| API Communication | REST APIs | Frontend/backend integration |
| Deployment | Docker + suitable cloud hosting | Application deployment |

### 3.1 API Responsibility

| API / Service | Purpose |
| --- | --- |
| OpenAI API | Resume analysis, content generation, interview feedback |
| OpenAI Embeddings API | Semantic resume and job matching |
| Adzuna API | Job discovery and job listings |
| Google OAuth API | User authentication |
| OpenAI Realtime API | Optional voice-based mock interviews |

Do not integrate every possible API immediately. Implement the essential integrations first and introduce optional services only when required.

### 3.2 Cost and Usage Management

- Centralize all LLM calls through a backend AI service.
- Configure model selection through environment variables.
- Set token limits and request timeouts.
- Track API usage per user.
- Cache embeddings where appropriate.
- Avoid repeatedly analyzing unchanged resumes.
- Add rate limits and usage quotas.
- Monitor API spending.
- Handle provider quota errors gracefully.

---

## 4. System Architecture

### 4.1 Architectural Approach

Implement IdeaMate AI using a **Modular Monolithic Architecture with Multi-Agent Orchestration**.

This approach provides:

- Clear separation of responsibilities.
- Independent feature development.
- Reusable business logic.
- Easier debugging and testing.
- Scalable integration management.
- Future migration to microservices if required.

Do not build the entire application inside one backend file or one frontend component.

### 4.2 High-Level Architecture

Reference: [Building an Adaptive RAG System with FastApi, Langgraph, ChromaDB, PostgreSQL and Docker](https://medium.com/%40binukajayaweera/building-an-adaptive-rag-system-with-fastapi-langgraph-chromadb-postgresql-and-docker-73b49fc736ed)

The architecture should follow this flow:

```text
                        IdeaMate AI
                              |
                     FRONTEND APPLICATION
               (Authentication & API Client)
                              |
                       FASTAPI BACKEND
                 (API ROUTER / CONTROLLERS)
                              |
                    APPLICATION SERVICES
          +-------------------+-------------------+
          |                   |                   |
     USER DOMAIN          JOB DOMAIN        RESUME DOMAIN
          |                   |                   |
          +-------------------+-------------------+
                              |
                  AI ORCHESTRATION (LANGGRAPH)
          +-------------------+-------------------+
          |                   |                   |
   Resume Analyst      Job Researcher      Interview Coach
          |                   |                   |
          +-------------------+-------------------+
                              |
                       OPENAI SERVICES
          +-------------------+-------------------+
          |                   |                   |
      PostgreSQL          ChromaDB          External APIs
          |                   |                   |
          +-------------------+-------------------+
                              |
                   APPROVAL & AUDIT LAYER
                              |
                      USER CONFIRMATION
                              |
                      EXTERNAL ACTIONS
```

### 4.3 Backend Architecture Principles

Follow these principles:

- **Separation of concerns:** API routes, business logic, AI services and database operations must remain separate.
- **Single responsibility:** Each module should perform one well-defined responsibility.
- **Dependency injection:** Services should receive their dependencies instead of creating global connections.
- **Repository pattern:** Database access should be separated from business logic.
- **Adapter pattern:** External APIs should be replaceable without changing core business logic.
- **Typed contracts:** Use Pydantic schemas and TypeScript interfaces.
- **Centralized configuration:** Environment variables should be managed in one configuration module.
- **Centralized exception handling:** Use consistent application errors and API responses.
- **Observability:** Track requests, background jobs, agent runs and external API failures.
- **Testability:** Every important module should be testable independently.

### 4.4 Recommended Project Structure

Use the following structure as a target. Adapt it to the existing repository rather than forcing unnecessary file movements.

```text
IdeaMate-ai/
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── routes/
│   │   │   └── providers/
│   │   ├── components/
│   │   │   ├── common/
│   │   │   ├── layout/
│   │   │   └── ui/
│   │   ├── features/
│   │   │   ├── dashboard/
│   │   │   ├── authentication/
│   │   │   ├── profile/
│   │   │   ├── resume/
│   │   │   ├── jobs/
│   │   │   ├── matching/
│   │   │   ├── documents/
│   │   │   ├── applications/
│   │   │   ├── interviews/
│   │   │   ├── skills/
│   │   │   └── settings/
│   │   ├── services/
│   │   │   ├── api-client.ts
│   │   │   └── auth-service.ts
│   │   ├── hooks/
│   │   ├── types/
│   │   ├── utils/
│   │   └── styles/
│   └── tests/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   ├── logging.py
│   │   │   ├── exceptions.py
│   │   │   └── dependencies.py
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── routers/
│   │   │       └── schemas/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── services/
│   │   ├── modules/
│   │   │   ├── authentication/
│   │   │   ├── profile/
│   │   │   ├── resume/
│   │   │   ├── jobs/
│   │   │   ├── matching/
│   │   │   ├── documents/
│   │   │   ├── applications/
│   │   │   ├── interviews/
│   │   │   ├── skills/
│   │   │   ├── memory/
│   │   │   ├── approvals/
│   │   │   └── reminders/
│   │   ├── agents/
│   │   │   ├── graph.py
│   │   │   ├── state.py
│   │   │   ├── nodes/
│   │   │   ├── prompts/
│   │   │   ├── tools/
│   │   │   └── policies.py
│   │   ├── integrations/
│   │   │   ├── openai/
│   │   │   ├── adzuna/
│   │   │   ├── oauth/
│   │   │   ├── chroma/
│   │   │   ├── storage/
│   │   │   └── document_parser/
│   │   ├── database/
│   │   │   ├── connection.py
│   │   │   └── migrations/
│   │   ├── workers/
│   │   └── observability/
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   ├── contract/
│   │   ├── agents/
│   │   └── e2e/
│   └── requirements.txt
│
├── infrastructure/
├── docs/
├── scripts/
├── .env.example
├── .gitignore
├── CLAUDE.md
└── README.md
```

**Important:** Do not create empty folders simply to match this diagram. Create modules when their implementation begins.

---

## 5. Database Design

Use PostgreSQL as the primary database.
ChromaDB should be used only for semantic retrieval, not as the primary source of application records.

### 5.1 Core Database Tables

| Table | Purpose |
| --- | --- |
| `users` | User account information |
| `user_profiles` | Personal and career profile |
| `resumes` | Uploaded resume metadata |
| `resume_facts` | Extracted and verified resume information |
| `user_skills` | User technical and soft skills |
| `jobs` | Normalized job listings |
| `job_matches` | Matching scores and explanations |
| `generated_documents` | Tailored resumes and cover letters |
| `applications` | Job application records |
| `application_history` | Application status changes |
| `interview_sessions` | Mock interview sessions |
| `interview_questions` | Generated questions |
| `interview_answers` | User responses |
| `interview_feedback` | AI evaluation results |
| `skill_gaps` | Identified missing skills |
| `career_memory` | User-approved memory |
| `approvals` | Pending and completed approvals |
| `reminders` | Application deadlines and reminders |
| `audit_logs` | Security and activity events |

### 5.2 Database Requirements

- Use UUID primary keys.
- Establish appropriate foreign key relationships.
- Add indexes for frequently queried fields.
- Use unique constraints to prevent duplicate records.
- Store timestamps in UTC.
- Store user timezone separately.
- Use Alembic for schema migrations.
- Never automatically modify production database schemas during application startup.
- Implement database transactions for critical operations.
- Use soft deletion only where there is a documented business or compliance reason.
- Implement account-level data isolation.

### 5.3 Resume Fact Verification

Resume extraction must not directly become trusted profile data.

Use the following process:

```text
Uploaded Resume
       |
       v
Text Extraction
       |
       v
AI Fact Extraction
       |
       v
Structured Resume Facts
       |
       v
Confidence / Evidence Validation
       |
       v
User Review and Correction
       |
       v
Verified Career Profile
```

- Store the evidence or source section associated with each important extracted fact.
- Only verified facts should be used for factual claims in tailored documents.

---

## 6. Backend API Development

All APIs should be versioned under: `/api/v1/`

### 6.1 Authentication APIs

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/auth/google` | Initiate Google login |
| `GET` | `/auth/google/callback` | OAuth callback |
| `POST` | `/auth/logout` | Logout |
| `GET` | `/auth/me` | Current user |

Implement secure session management and validate OAuth/OIDC responses.

### 6.2 Profile APIs

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/profile` | Get profile |
| `POST` | `/profile` | Create profile |
| `PUT` | `/profile` | Update profile |
| `GET` | `/profile/skills` | Get user skills |
| `PUT` | `/profile/skills` | Update skills |

### 6.3 Resume APIs

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/resumes/upload` | Upload resume |
| `GET` | `/resumes` | List resumes |
| `GET` | `/resumes/{resume_id}` | Get resume |
| `POST` | `/resumes/{resume_id}/analyze` | Analyze resume |
| `GET` | `/resumes/{resume_id}/analysis` | Get analysis |
| `PATCH` | `/resumes/{resume_id}/facts` | Update extracted facts |
| `DELETE` | `/resumes/{resume_id}` | Delete resume |

### 6.4 Job APIs

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/jobs/search` | Search jobs |
| `GET` | `/jobs/{job_id}` | Get job details |
| `POST` | `/jobs/{job_id}/match` | Calculate match |
| `GET` | `/jobs/recommended` | Recommended jobs |
| `POST` | `/jobs/{job_id}/save` | Save job |

### 6.5 Document APIs

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/documents/tailor-resume` | Generate tailored resume |
| `POST` | `/documents/cover-letter` | Generate cover letter |
| `POST` | `/documents/application-note` | Generate short note |
| `GET` | `/documents/{document_id}` | Get document |
| `PATCH` | `/documents/{document_id}` | Edit document |
| `GET` | `/documents/{document_id}/download` | Download document |

### 6.6 Application APIs

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/applications` | List applications |
| `POST` | `/applications` | Create application |
| `GET` | `/applications/{application_id}` | Application details |
| `PATCH` | `/applications/{application_id}` | Update application |
| `POST` | `/applications/{application_id}/transition` | Change status |
| `DELETE` | `/applications/{application_id}` | Delete application |

### 6.7 Interview APIs

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/interviews` | Create session |
| `GET` | `/interviews` | List sessions |
| `GET` | `/interviews/{session_id}` | Get session |
| `POST` | `/interviews/{session_id}/questions` | Generate questions |
| `POST` | `/interviews/{session_id}/answers` | Submit answer |
| `POST` | `/interviews/{session_id}/evaluate` | Evaluate answers |
| `GET` | `/interviews/{session_id}/feedback` | Get feedback |

### 6.8 Additional APIs

Create separate endpoints for:

- Skill gap analysis.
- Career memory.
- Approval management.
- Reminder management.
- Dashboard analytics.
- Account export and deletion.

**API standards:**

- Use Pydantic request and response schemas.
- Validate request parameters.
- Apply authentication and authorization.
- Use consistent error responses.
- Implement pagination for list endpoints.
- Add request IDs for traceability.
- Use idempotency keys for retry-sensitive operations.
- Never expose internal stack traces to users.

---

## 7. Multi-Agent AI Architecture

The multi-agent system is one of the central technical components of IdeaMate AI.
Implement agents as independent modules with clearly defined responsibilities.
Do not place all AI functionality inside one large agent or one prompt.

### 7.1 Agent Responsibilities

1. **Resume Analyst Agent** (Resume Intelligence)
   - Extract resume information.
   - Identify skills and experience.
   - Analyze projects and education.
   - Generate structured career facts.
2. **Job Researcher Agent** (Job Discovery)
   - Understand target roles.
   - Retrieve job opportunities through authorized APIs.
   - Normalize job descriptions.
   - Identify relevant opportunities.
3. **Job Matching Agent** (Intelligent Matching)
   - Compare job requirements with verified skills.
   - Calculate matching factors.
   - Identify missing skills.
   - Generate match explanations.
4. **Resume Tailoring Agent** (Document Generation)
   - Analyze selected job requirements.
   - Select relevant verified experience.
   - Generate tailored resume content.
   - Validate factual consistency.
5. **Cover Letter Agent** (Application Preparation)
   - Generate job-specific cover letters.
   - Generate short application notes.
   - Maintain professional and contextual content.
6. **Interview Coach Agent** (Interview Preparation)
   - Generate role-specific questions.
   - Evaluate answers.
   - Identify weak areas.
   - Recommend improvements.
7. **Career Memory Agent** (Personalization)
   - Retrieve approved career preferences.
   - Maintain user-approved progress information.
   - Update memory only under the defined consent policy.

### 7.2 Agent Orchestration Using LangGraph

Use LangGraph to coordinate the agents.

Each agent must have:

- Clearly defined input schema.
- Clearly defined output schema.
- Independent prompt template.
- Access only to required tools.
- Error-handling mechanism.
- Timeout and retry limits.
- Execution tracing.
- Token and cost limits.

Suggested workflow:

```text
               USER REQUEST
                    |
                    v
            REQUEST VALIDATION
                    |
                    v
             LOAD USER PROFILE
                    |
                    v
             TASK CLASSIFIER
         +----------+----------+
         |          |          |
         v          v          v
      RESUME       JOB     INTERVIEW
     ANALYSIS   DISCOVERY   COACHING
         |          |
         v          v
      VERIFY    NORMALIZE
      FACTS     JOB DATA
         |          |
         v          |
       MATCH        |
         |          |
         +----------+
               |
               v
        DOCUMENT DRAFT
               |
               v
        FACT VALIDATION
               |
               v
         USER APPROVAL
               |
               v
        EXECUTE ACTION
               |
               v
           AUDIT LOG
```

Not every workflow should execute every agent. Route tasks only to the necessary specialists.

### 7.3 Agent State Management

Maintain a typed workflow state containing:

- User ID.
- Workflow ID.
- Requested task.
- Verified profile reference.
- Job reference.
- Current processing stage.
- Agent outputs.
- Validation results.
- Pending approval ID.
- Execution status.
- Error details.

Use persistent checkpoints for workflows that may pause for user input or approval.

### 7.4 Agent Safety

- Do not allow agents to override application permissions.
- Do not let retrieved job descriptions issue executable instructions.
- Do not expose database credentials or unrestricted database access to agents.
- Restrict tools to specific actions.
- Limit execution steps.
- Limit LLM token usage.
- Validate structured outputs.
- Log tool execution.
- Require user approval for external side effects.

---

## 8. RAG and Vector Database Implementation

Use Retrieval-Augmented Generation where contextual retrieval improves the results.

### 8.1 RAG Use Cases

- Resume and career fact retrieval.
- Semantic job matching.
- Skill requirement retrieval.
- Interview preparation using selected role/job context.
- Relevant career information retrieval.

### 8.2 RAG Pipeline

```text
SOURCE DOCUMENTS -> TEXT EXTRACTION -> TEXT CLEANING -> CHUNKING
  -> EMBEDDING GENERATION -> CHROMADB STORAGE

USER QUERY -> SEMANTIC RETRIEVAL -> RELEVANT CONTEXT
  -> OPENAI LLM -> VALIDATED RESPONSE
```

### 8.3 Implementation Standards

- Use consistent chunking strategies.
- Store document and user metadata.
- Isolate retrieval by user ownership.
- Use content hashes to avoid duplicate embedding generation.
- Store embedding model and version metadata.
- Support document updates and deletion.
- Avoid retrieving unrelated user information.
- Validate retrieved context before sending it to an LLM.
- Use ChromaDB through a dedicated vector-store interface so that another vector database can be introduced later without rewriting business logic.

---

## 9. Core Feature Implementation Details

This section defines how each major feature should be implemented internally.

### 9.1 Resume Processing Pipeline

Implementation sequence:

1. Accept PDF/DOCX uploads.
2. Validate file type, size and file signature.
3. Store the original file in private storage.
4. Create a resume database record.
5. Trigger asynchronous parsing.
6. Extract text using document parsing utilities.
7. Pass extracted text to the Resume Analyst Agent.
8. Validate the returned structured JSON.
9. Store extracted facts with evidence and confidence.
10. Display the extracted information for user review.
11. Save user-verified information to the career profile.
12. Generate embeddings for relevant approved content.

Use separate services:

```text
resume/
├── router.py
├── schemas.py
├── models.py
├── repository.py
├── service.py
├── parser.py
├── extractor.py
├── validator.py
└── tasks.py
```

Do not combine parsing, LLM extraction, database operations and file generation in one service.

### 9.2 Job Discovery Pipeline

```text
User Search Preferences
       |
       v
Job Search Service
       |
       v
Adzuna Provider Adapter
       |
       v
External Job API
       |
       v
Response Normalization
       |
       v
Duplicate Detection
       |
       v
Database Persistence
       |
       v
Job Matching Service
       |
       v
Ranked Job Results
       |
       v
Frontend Dashboard
```

Requirements:

- Cache suitable search responses.
- Respect external provider rate limits.
- Handle missing job descriptions.
- Preserve original job URLs.
- Track posting and retrieval dates.
- Avoid duplicate listings.
- Handle expired and unavailable listings.
- Display source information.
- Never present mock job data as live job results.

### 9.3 Job Matching Algorithm

Begin with an explainable weighted scoring system.

| Matching factor | Initial weight |
| --- | --- |
| Technical skill compatibility | 35% |
| Job role similarity | 20% |
| Relevant experience/projects | 20% |
| Experience-level compatibility | 10% |
| Education requirements | 5% |
| Location preferences | 5% |
| Job freshness | 5% |
| **Total** | **100%** |

These are initial configurable weights, not scientifically validated hiring criteria. Validate and adjust them through testing and user feedback.

Suggested formula:

$$M = \sum_{i=1}^{n} w_i s_i$$

Where:
- $M$ = overall match score.
- $w_i$ = factor weight.
- $s_i$ = normalized factor score between 0 and 1.

Implementation requirements:

- Keep scoring logic independent of the LLM.
- Store individual factor scores.
- Make weights configurable.
- Version the scoring algorithm.
- Explain why a job matches.
- Identify missing skills.
- Do not use sensitive personal attributes or their proxies.

### 9.4 Resume Tailoring Workflow

```text
Selected Job -> Analyze Job Requirements -> Retrieve Verified Resume Facts
  -> Identify Relevant Experience -> Generate Tailored Draft -> Check Unsupported Claims
  -> Create Editable Document -> User Review -> Export PDF / DOCX
```

Important requirements:

- Maintain the original resume.
- Maintain generated versions.
- Store the job reference used for tailoring.
- Preserve user edits.
- Validate dates, employers, skills and experience.
- Never invent achievements.
- Provide a document preview before export.

### 9.5 Mock Interview Evaluation

Use a structured evaluation rubric.

| Evaluation category | Purpose |
| --- | --- |
| Technical correctness | Accuracy of technical response |
| Conceptual understanding | Understanding of the underlying concept |
| Problem-solving | Logical approach |
| Communication | Clarity and organization |
| Relevance | Whether the answer addresses the question |
| Completeness | Coverage of important points |

Expected output:

```json
{
  "overall_feedback": "Clear explanation with room for improvement.",
  "strengths": [
    "Good understanding of the concept"
  ],
  "improvements": [
    "Include a practical example"
  ],
  "technical_accuracy": 8,
  "communication": 7,
  "problem_solving": 7,
  "recommended_topics": [
    "REST API fundamentals",
    "Database indexing"
  ]
}
```

Scores are illustrative. Define and document a consistent scoring rubric before production.

### 9.6 Application Tracker State Machine

Use a controlled state transition system.

```text
SAVED
  |
  v
PREPARING
  |
  v
AWAITING_APPROVAL
  |
  v
SUBMITTED
  +--------------------+--------------------+
  |                    |                    |
  v                    v                    v
INTERVIEW           REJECTED              OFFER
  |                                         |
  +--------------------+--------------------+
                       |
                       v
                   WITHDRAWN
```

- Implement transition validation in the backend.
- The frontend must not be allowed to directly assign arbitrary status values.

### 9.7 Reminder System

Implement reminders through a background worker and scheduler.

Examples:

- Application deadline.
- Interview date.
- Recruiter follow-up.
- Resume improvement task.
- Interview practice schedule.

Requirements:

- Store timestamps in UTC.
- Use the user's timezone for scheduling and display.
- Support cancellation.
- Prevent duplicate reminders.
- Track delivery status.
- Retry temporary delivery failures.
- Respect notification preferences and consent.

---

## 10. Frontend Implementation Standards

The existing Orbit prototype must remain the visual foundation.

### 10.1 Frontend Feature Organization

Each major feature should contain its own:

- Page or route.
- Components.
- API integration.
- Types.
- Hooks/state management.
- Validation.
- Tests.

Example:

```text
features/
  jobs/
    components/
      JobCard.tsx
      JobFilters.tsx
      MatchScore.tsx
      JobDetails.tsx
    hooks/
      useJobs.ts
      useJobMatch.ts
    services/
      jobService.ts
    types/
      job.types.ts
    pages/
      JobsPage.tsx
      JobDetailsPage.tsx
    tests/
      jobService.test.ts
```

Adapt filenames and conventions to the current framework.

### 10.2 UI Requirements

For every feature, implement:

- Initial state.
- Loading state.
- Success state.
- Empty state.
- Error state.
- Validation state.
- Responsive behavior.

### 10.3 Frontend Best Practices

- Use reusable components.
- Avoid unnecessarily large page components.
- Separate API calls from UI components.
- Use centralized API configuration.
- Use typed request and response models.
- Avoid duplicate API requests.
- Implement appropriate caching and invalidation.
- Handle authentication expiry.
- Prevent accidental repeated form submissions.
- Provide user-friendly error messages.
- Use accessible forms and controls.
- Preserve the existing design system and styling tokens.

### 10.4 Frontend Performance

- Lazy-load appropriate routes.
- Optimize large lists using pagination or virtualization when necessary.
- Avoid unnecessary component re-renders.
- Compress and optimize images.
- Use code splitting.
- Avoid loading unnecessary AI results on initial dashboard rendering.
- Keep expensive operations asynchronous.

---

## 11. Security and Privacy Standards

Security must be considered from the beginning, not added after implementation.

### 11.1 Authentication

- Implement OAuth/OIDC securely.
- Validate authorization state and nonce.
- Validate issuer, audience and token expiry.
- Use secure session management.
- Implement logout and session revocation.
- Avoid storing passwords unnecessarily.

### 11.2 Authorization

Every protected resource must be checked against the authenticated user's ownership.

For example:

```python
resume = await resume_repository.get_by_id(resume_id)
if resume is None or resume.user_id != current_user.id:
    raise NotFoundError("Resume not found")
```

Apply equivalent ownership checks to applications, documents, interviews, memory and other private resources.

### 11.3 File Security

- Allow only supported file formats.
- Verify file signatures.
- Limit file size and document pages.
- Scan uploads where appropriate.
- Use private storage.
- Use short-lived download URLs.
- Prevent path traversal.
- Never execute uploaded files.

### 11.4 API Security

- Validate all inputs.
- Implement rate limiting.
- Restrict CORS.
- Configure safe error handling.
- Use request timeouts.
- Protect against CSRF where applicable.
- Keep dependencies updated.
- Use HTTPS in production.

### 11.5 AI Security

- Protect against prompt injection.
- Treat retrieved content as untrusted.
- Restrict agent tools.
- Validate LLM-generated JSON.
- Prevent cross-user retrieval.
- Never expose credentials to agents.
- Require approval for external side effects.

### 11.6 Privacy

- Obtain consent for optional data storage and notifications.
- Explain what information is sent to AI providers.
- Provide account data export and deletion.
- Define document and interview data retention.
- Do not log full resumes or sensitive prompt payloads.
- Do not use protected characteristics for job ranking.

---

## 12. Performance and Scalability

Implement the following production standards.

| Area | Requirement |
| --- | --- |
| Database | Indexing, connection pooling and optimized queries |
| API | Async operations, pagination and request validation |
| AI | Token limits, caching and bounded retries |
| Job discovery | Provider caching and duplicate detection |
| Documents | Background parsing and generation |
| Agents | Checkpointing, execution limits and tracing |
| Frontend | Lazy loading and optimized rendering |
| Storage | Private object storage and signed URLs |
| Reliability | Timeout handling and graceful degradation |
| Monitoring | Logs, metrics and error tracking |

### 12.1 Background Processing

Use background workers for:

- Resume parsing.
- Resume analysis.
- Embedding generation.
- Large job discovery tasks.
- Bulk job matching.
- Document generation.
- Interview evaluation.
- Reminder delivery.

The API should return a task identifier or resource status when a task takes significant time.

Example:

```json
{
  "task_id": "task-uuid",
  "status": "processing",
  "message": "Resume analysis has started."
}
```

Provide a status endpoint to retrieve the result.

### 12.2 Error Handling

Implement centralized exception handling for:

- Authentication failures.
- Authorization failures.
- Validation errors.
- Database errors.
- LLM failures.
- External API failures.
- File parsing failures.
- Background task failures.

Use bounded retries with exponential backoff for transient failures.
Never retry permanent validation or authorization errors.

---

## 13. Step-by-Step Implementation Roadmap

Claude Code must implement the application in phases. Each phase should produce working, testable functionality before moving to the next.

### Implementation Sequence

- **Phase 0 — Existing Project Analysis** *(First priority)*: Inspect the current prototype, framework, routes, dependencies, design system and existing functionality.
- **Phase 1 — Architecture and Backend Foundation**: Backend structure, database, configuration, logging, API conventions and health checks.
- **Phase 2 — Authentication and User Profile**: OAuth, sessions, user profile management and authorization.
- **Phase 3 — Resume Intelligence**: Upload, parsing, AI extraction, verification and career profile.
- **Phase 4 — Job Discovery and Matching**: Job API integration, normalization, filtering and matching algorithm.
- **Phase 5 — AI Document Generation**: Tailored resumes, cover letters, editing, versioning and export.
- **Phase 6 — Application Tracking**: Application management, status transitions, activity and deadlines.
- **Phase 7 — Multi-Agent Architecture**: LangGraph, specialist agents, RAG, workflow persistence and approval controls.
- **Phase 8 — Interview Preparation**: Question generation, answer evaluation, feedback and skill gap analysis.
- **Phase 9 — Career Memory and Reminders**: Persistent user-approved preferences, progress and notifications.
- **Phase 10 — Production Hardening**: Security, performance, testing, monitoring, deployment and documentation.

### Phase 0 — Repository Analysis

Before writing code, Claude Code must:

- Inspect the entire project directory.
- Identify frontend and backend frameworks.
- Review package manifests and dependencies.
- Identify all existing routes and pages.
- Identify reusable UI components.
- Inspect existing API integrations.
- Identify mock data and incomplete functionality.
- Run the existing application.
- Run the existing test suite.
- Identify existing errors and technical limitations.

Deliverables:

- Existing architecture report.
- Frontend route inventory.
- Component inventory.
- Existing functionality checklist.
- Dependency analysis.
- Proposed implementation plan.
- List of required changes.

Do not delete or replace existing functionality during this phase.

### Phase 1 — Backend Foundation

Implement:

- FastAPI application initialization.
- Modular configuration.
- PostgreSQL connection.
- ORM models.
- Alembic migrations.
- Centralized logging.
- Exception handling.
- API versioning.
- Health endpoints.
- Environment configuration.
- Local development setup.

Completion criteria: Backend starts successfully; database connects successfully; initial migration runs; health endpoints work; configuration validation works; basic unit tests pass.

### Phase 2 — Authentication and Profile

Implement:

- Google OAuth/OIDC.
- User creation and login.
- Session handling.
- Protected API routes.
- User profile CRUD.
- Career preferences.
- Skills management.

Completion criteria: Authentication works; user profile persists; unauthorized access is rejected; cross-user data access is prevented.

### Phase 3 — Resume Intelligence

Implement:

- Secure resume upload.
- PDF/DOCX parsing.
- Text extraction.
- Structured AI extraction.
- Skill identification.
- Education and experience extraction.
- Project extraction.
- Resume analysis.
- User verification.
- Career profile synchronization.

Completion criteria: A student can upload a resume, review extracted information, correct it and save a verified career profile.

### Phase 4 — Job Discovery and Matching

Implement:

- Adzuna API adapter.
- Search filters.
- Job normalization.
- Duplicate detection.
- Job persistence.
- Job description retrieval.
- Skill matching.
- Semantic matching.
- Explainable score generation.

Completion criteria: The student receives actual sourced job listings with understandable matching explanations.

### Phase 5 — Document Generation

Implement:

- Job description analysis.
- Verified resume fact retrieval.
- Tailored resume generation.
- Cover letter generation.
- Application note generation.
- Factuality validation.
- Editable document versions.
- PDF/DOCX export.

Completion criteria: A student can generate, edit and download a job-specific document without modifying the original resume.

### Phase 6 — Application Tracking

Implement:

- Application creation.
- Job association.
- Status management.
- Validated transitions.
- Application history.
- Notes.
- Deadlines.
- Dashboard integration.

Completion criteria: Application records persist correctly and the tracker reflects the actual stored state.

### Phase 7 — Multi-Agent System

Implement:

- LangGraph initialization.
- Shared typed state.
- Specialist agent nodes.
- Independent prompts.
- Tool definitions.
- RAG retrieval.
- Workflow checkpointing.
- Execution tracing.
- Retry policies.
- Human approval integration.

Completion criteria: Each agent performs its defined task independently, and multi-step workflows can pause, resume and recover from failures.

### Phase 8 — Interview Preparation

Implement:

- Role-based question generation.
- Technical question generation.
- HR and behavioral questions.
- Answer submission.
- Rubric-based evaluation.
- Feedback generation.
- Weakness identification.
- Skill improvement plan.

Completion criteria: A student can complete a mock interview and retrieve structured feedback.

### Phase 9 — Memory and Reminders

Implement:

- Career memory CRUD.
- Memory consent.
- User preferences.
- Progress tracking.
- Reminder scheduling.
- Timezone handling.
- Notification delivery.
- Cancellation and retry mechanisms.

Completion criteria: User-approved information persists correctly and reminders are delivered without duplication.

### Phase 10 — Production Hardening

Implement:

- Security testing.
- Performance optimization.
- Database optimization.
- Frontend accessibility.
- Error monitoring.
- Application logging.
- CI/CD.
- Docker deployment.
- Backup and restore.
- Production documentation.

Completion criteria: All critical workflows work in a production-like environment, with no unresolved critical security issues.

---

## 14. Testing Strategy

Testing must be implemented alongside development, not postponed until the end.

### 14.1 Testing Levels

| Testing type | Purpose | Suggested tools |
| --- | --- | --- |
| Unit testing | Validate individual functions and business rules | Pytest, Vitest |
| Integration testing | Validate database and service interactions | Pytest, HTTPX |
| API testing | Validate API contracts and responses | Postman, HTTPX |
| Frontend testing | Validate components and UI behavior | Testing Library |
| E2E testing | Validate complete user journeys | Playwright |
| Agent testing | Validate AI workflows and tool restrictions | Pytest |
| Security testing | Identify vulnerabilities | Bandit, pip-audit |
| Performance testing | Evaluate system performance | Locust, k6 |
| Accessibility testing | Validate accessibility | axe-core |

Adapt frontend testing tools to the actual framework discovered during repository analysis.

### 14.2 Mandatory Unit Tests

- **Authentication:** Valid login; Invalid OAuth callback; Expired session; Unauthorized requests.
- **Resume:** Valid PDF upload; Valid DOCX upload; Invalid file format; Oversized file; Empty document; Parsing failure; Incorrect extracted data; User fact correction.
- **Job matching:** Exact skill match; Partial skill match; Missing required skills; Experience mismatch; Location mismatch; Empty job description.
- **Applications:** Valid status transitions; Invalid status transitions; Duplicate application prevention; Application ownership validation.
- **AI:** Valid structured response; Malformed JSON; Missing fields; LLM timeout; Token limit exceeded; Unsupported factual claims; Prompt injection attempts.

### 14.3 Integration Testing

Verify:

- PostgreSQL connections.
- Database migrations.
- Resume storage.
- Document parsing.
- OpenAI API integration.
- Adzuna API integration.
- ChromaDB persistence.
- OAuth authentication.
- LangGraph execution.
- Approval persistence.
- Background worker execution.

Use mocked provider responses for deterministic tests, with a separate controlled integration test environment for real provider connectivity.

### 14.4 End-to-End Testing

The following scenarios are mandatory:

- **Scenario 1 — Complete Resume Workflow:** User signs in -> Uploads resume -> AI extracts information -> User verifies extracted details -> Profile gets updated.
- **Scenario 2 — Job Discovery and Matching:** User selects target role -> System retrieves job listings -> Matching algorithm calculates scores -> User views matching explanations -> User saves a job.
- **Scenario 3 — Job-Specific Application Preparation:** User selects a job -> AI prepares a tailored resume -> AI generates a cover note -> User edits and downloads documents -> Application is added to the tracker.
- **Scenario 4 — Human Approval:** System prepares an external action -> User reviews the exact content and destination -> User approves or rejects -> System executes only if approved -> Result is recorded in the audit log.
- **Scenario 5 — Mock Interview:** User selects a target role -> AI generates questions -> User submits answers -> AI evaluates the responses -> User receives feedback and improvement recommendations.

### 14.5 AI Quality Testing

AI output must be evaluated for:

- Accuracy.
- Relevance.
- Factual consistency.
- Structured output validity.
- Hallucination.
- Prompt injection resistance.
- Reproducibility where deterministic behavior is expected.
- Token usage.
- Response latency.

Create a fixed evaluation dataset with representative resumes, job descriptions, interview answers and expected constraints.
Do not evaluate AI quality using only a few manually selected successful examples.

### 14.6 Performance Testing

Test the application under:

- Multiple simultaneous users.
- Multiple resume uploads.
- Concurrent job searches.
- Multiple agent workflows.
- Large resume documents within supported limits.
- External API delays.
- Database load.
- Background task backlogs.

Establish measurable latency and throughput targets after measuring the initial implementation. Do not claim production performance without load-test evidence.

---

## 15. Production Code Quality Standards

Claude Code must follow these standards throughout implementation.

### 15.1 Python Standards

- Follow PEP 8.
- Use type hints.
- Use Pydantic schemas.
- Use asynchronous operations where beneficial.
- Avoid circular imports.
- Use dependency injection.
- Use structured logging.
- Avoid unnecessary global variables.
- Separate database operations from business logic.
- Handle exceptions explicitly.
- Document complex functions.

Recommended tools: Ruff, Pytest, Mypy or Pyright, Coverage.

### 15.2 Frontend Standards

- Follow existing framework conventions.
- Use reusable components.
- Keep components focused.
- Use TypeScript types if the project is TypeScript-based.
- Avoid duplicated business logic.
- Centralize API communication.
- Handle asynchronous state correctly.
- Use accessible UI components.
- Keep styling consistent.

### 15.3 Code Review Rules

Before completing each feature, check:

- Is the code modular?
- Is the responsibility clear?
- Is the implementation reusable?
- Are API responses validated?
- Are errors handled?
- Are authorization checks present?
- Are tests included?
- Are secrets protected?
- Does the implementation preserve existing functionality?
- Is unnecessary complexity avoided?

### 15.4 Documentation Requirements

Maintain:

```text
docs/
├── architecture.md
├── database-schema.md
├── api-documentation.md
├── agent-workflows.md
├── security.md
├── deployment.md
├── testing.md
└── troubleshooting.md
```

Update documentation when the implementation changes.

---

## 16. Environment Configuration

Use environment variables for all sensitive credentials and deployment-specific configuration.

Example `.env.example`:

```dotenv
# Application
APP_ENV=development
APP_SECRET_KEY=
DEBUG=false

# Database
DATABASE_URL=

# Redis
REDIS_URL=

# OpenAI
OPENAI_API_KEY=
OPENAI_MODEL=
OPENAI_EMBEDDING_MODEL=

# Adzuna
ADZUNA_APP_ID=
ADZUNA_APP_KEY=

# Google OAuth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=

# ChromaDB
CHROMA_URL=

# Storage
STORAGE_PROVIDER=
STORAGE_BUCKET=

# Frontend
FRONTEND_URL=
CORS_ALLOWED_ORIGINS=

# Monitoring
LOG_LEVEL=INFO
```

Requirements:

- Never commit `.env`.
- Keep `.env.example` updated.
- Validate required configuration during application startup.
- Use separate development, testing, staging and production configurations.
- Use a secrets manager for production credentials.
- Never expose backend credentials to frontend code.

---

## 17. Deployment and DevOps

### 17.1 Development Environment

Use Docker Compose where appropriate for local dependencies.

Recommended development services: Frontend, FastAPI backend, PostgreSQL, Redis, ChromaDB, Background worker.

### 17.2 Production Deployment

Separate application processes where appropriate:

```text
                    PRODUCTION
                        |
                  LOAD BALANCER
          +-------------+-------------+
          |                           |
      API SERVER                  API SERVER
          |                           |
          +-------------+-------------+
                        |
                     DATABASE
          +-------------+-------------+
          |                           |
        REDIS                      CHROMADB
          |
     WORKER QUEUE
          |
  BACKGROUND WORKERS
```

Use managed database and private object storage services where practical.

### 17.3 CI/CD Pipeline

Every code change should pass through:

```text
Developer Push -> Code Formatting -> Linting -> Type Checking -> Unit Tests
  -> Integration Tests -> Security Scanning -> Build Validation
  -> Deployment to Staging -> Smoke Tests -> Production Deployment
```

Production deployment should include controlled database migrations, health checks and a rollback strategy.

---

## 18. Monitoring and Observability

Implement monitoring for both conventional application functionality and AI workflows.

| Metric | What to monitor |
| --- | --- |
| API latency | Response times |
| API errors | Failed requests |
| Database | Connection health and query performance |
| OpenAI | Token consumption, latency and errors |
| Adzuna | API availability and quota |
| Agent workflows | Execution duration and failures |
| Background jobs | Queue depth and failed tasks |
| Resume processing | Parsing and extraction failures |
| Application actions | Approval and execution outcomes |
| Security | Unauthorized access attempts |

Use structured JSON logging.

Every important workflow should have:

- Request ID.
- Workflow ID.
- User's internal identifier.
- Execution stage.
- Timestamp.
- Status.
- Error information where applicable.

Do not log complete resume contents, credentials or unnecessary personal information.

---

## 19. Future Scalability and Enhancements

The initial release should focus on the complete core placement workflow.
Future features can be introduced without changing the existing core architecture.

| Enhancement | Possible implementation |
| --- | --- |
| Voice-based interviews | OpenAI Realtime API |
| Advanced job matching | Improved semantic and hybrid retrieval |
| Recruiter communication | Approved email integrations |
| Calendar integration | Google Calendar API |
| Notifications | Email and push notifications |
| Coding assessments | Authorized coding assessment APIs |
| University placement portal | Institution-level dashboards |
| Placement analytics | Aggregate placement insights |
| Advanced agent collaboration | Additional LangGraph workflows |
| Career learning recommendations | Personalized learning engine |

Keep optional integrations behind interfaces and feature flags.
Do not introduce unnecessary dependencies before the corresponding feature is required.

---

## 20. Claude Code Implementation Instructions

This section is the primary execution instruction for Claude Code.
The following instructions must be treated as implementation constraints.

### 20.1 General Instructions

- Analyze the existing repository before modifying files.
- Preserve the existing Orbit prototype and its functional behavior.
- Follow the modular architecture defined in this document.
- Implement functionality incrementally.
- Avoid monolithic components and backend services.
- Keep AI prompts separate from business logic.
- Keep database operations separate from API routes.
- Use reusable integration adapters.
- Implement automated tests for every important feature.
- Follow security and privacy requirements.
- Maintain documentation.
- Never introduce mock responses into production functionality without clearly identifying demo mode.

### 20.2 Development Workflow

For every feature, follow this sequence:

1. Understand requirements
2. Inspect existing implementation
3. Design module boundaries
4. Define API contracts
5. Implement backend services
6. Implement database operations
7. Implement frontend integration
8. Add validation and error handling
9. Write automated tests
10. Run tests and review changes
11. Update documentation
12. Mark feature complete

### 20.3 Claude Code Must Not

- Rewrite the existing application unnecessarily.
- Delete working features.
- Put all backend logic into `main.py`.
- Put all frontend functionality into one page component.
- Combine every AI agent into one prompt.
- Hardcode API keys.
- Use mock job listings as real opportunities.
- Generate fictional resume achievements.
- Skip backend authorization.
- Execute external actions without human approval.
- Ignore failing tests.
- Introduce dependencies without justification.
- Claim that a feature is complete when it is only a UI mockup.

### 20.4 Mandatory Completion Report

At the end of every implementation phase, Claude Code must report:

- Features implemented.
- Architecture decisions.
- Files created.
- Files modified.
- Database changes.
- APIs implemented.
- Integrations completed.
- Tests executed.
- Test results.
- Known issues.
- Remaining tasks.
- Next implementation phase.

---

## 21. Master Prompt for Claude Code

Use the following as the main implementation instruction after placing this specification in the project repository as `docs/IMPLEMENTATION_SPEC.md`.

> **MASTER IMPLEMENTATION PROMPT — IdeaMate AI**
>
> You are the lead software architect and senior full-stack AI engineer responsible for implementing IdeaMate AI, an intelligent placement co-pilot for students.
> Your responsibility is to transform the existing Orbit prototype into a fully functional, modular, secure and production-ready application.
> Treat `docs/IMPLEMENTATION_SPEC.md` as the primary technical implementation reference.
>
> **1. First: Analyze the Existing Project**
> Before writing or modifying code:
> - Inspect the complete repository structure.
> - Identify the existing frontend and backend technologies.
> - Review all routes, components, pages, styles and integrations.
> - Identify existing working functionality.
> - Identify mock data and incomplete implementations.
> - Run the application and existing test suite.
> - Document the current architecture and technical limitations.
> Do not immediately rebuild the application. Preserve existing functionality, visual design, routes, interactions and reusable components.
>
> **2. Architecture Requirements**
> Implement a modular monolithic architecture with clear domain boundaries.
> Separate: Frontend features and components; API routers and schemas; Application services; Domain models and business rules; Database repositories; AI agents and orchestration; External integrations; Background workers; Security and authorization; Testing and observability.
> Use FastAPI, PostgreSQL, LangGraph, OpenAI API and ChromaDB according to the specification, while retaining the existing frontend framework.
> Avoid monolithic files, duplicated logic, unnecessary abstractions and premature microservices.
>
> **3. Product Features**
> Implement the following modules: Authentication and user profiles; Resume upload and intelligent analysis; Career profile and skills extraction; Job discovery; Intelligent job matching; Job-specific resume tailoring; Cover letter and application note generation; Application tracking; AI mock interviews; Skill gap analysis; Personalized career memory; Human approval and external action management; Reminders and notifications; Dashboard and analytics.
> Refer to the implementation specification for detailed requirements.
>
> **4. Multi-Agent Implementation**
> Use LangGraph for agent orchestration.
> Implement independent specialist modules for: Resume analysis; Job research; Job matching; Resume tailoring; Cover letter generation; Interview coaching; Career memory.
> Each agent must have typed input/output schemas, separate prompts, restricted tools, error handling, execution limits and appropriate logging.
> Use RAG and ChromaDB for relevant semantic retrieval.
> Never allow AI-generated instructions or retrieved job descriptions to bypass system policies.
>
> **5. Human Approval**
> Human approval is mandatory before: Submitting job applications; Sending recruiter communications; Uploading documents externally; Executing other external side effects.
> Display the exact destination and content before approval.
> Bind approval to the exact action payload. Invalidate it if the content or destination changes.
> Never assume approval from previous actions.
>
> **6. Production Standards**
> Implement: Secure authentication and authorization; User-level data isolation; Input validation; Centralized exception handling; Structured logging; Database migrations; API versioning; Background processing; Rate limiting; Caching where appropriate; Idempotent operations; AI usage limits; Secure file storage; Performance optimization; Automated testing; CI/CD readiness; Monitoring and deployment documentation.
> Never hardcode credentials. Never fabricate job listings or resume facts.
>
> **7. Implementation Strategy**
> Work in the following order:
> - Phase 0: Repository analysis and preservation mapping.
> - Phase 1: Backend and database foundation.
> - Phase 2: Authentication and profile management.
> - Phase 3: Resume intelligence.
> - Phase 4: Job discovery and matching.
> - Phase 5: Resume tailoring and document generation.
> - Phase 6: Application tracking.
> - Phase 7: Multi-agent orchestration and RAG.
> - Phase 8: Interview preparation and skill analysis.
> - Phase 9: Career memory and reminders.
> - Phase 10: Security, performance, testing and deployment.
> Complete and validate each phase before proceeding.
>
> **8. Testing Requirements**
> Write unit, integration, API, agent workflow and end-to-end tests.
> Test critical user journeys and security boundaries.
> Validate: Cross-user data isolation; Resume upload and parsing; Factual accuracy of generated documents; Job matching behavior; Application status transitions; Approval enforcement; Agent failure recovery; API error handling; Background task idempotency; Performance and accessibility.
> Do not ignore failing tests or hide errors.
>
> **9. Development Discipline**
> For every implementation phase:
> Explain the implementation plan; Identify the modules involved; Make focused code changes; Preserve existing functionality; Add or update tests; Run formatters, linters and type checks; Run relevant tests; Review the complete code diff; Update documentation; Report completion and remaining risks.
> Do not attempt to implement the entire product in one massive code generation step.
> If a technical decision conflicts with the existing repository, explain the trade-off and propose a safe adaptation before making a breaking change.
>
> **10. Final Objective**
> Deliver a fully working IdeaMate AI application, not merely a frontend demonstration.
> The final application must provide a reliable end-to-end placement assistance workflow with modular architecture, explainable AI functionality, secure user data, human-controlled external actions, automated testing and production-ready operational documentation.
> Begin with Phase 0: inspect the repository and prepare the implementation plan. Do not start large-scale code modifications before completing the analysis.

---

## 22. Final Definition of Done

The project should be considered production-ready only when the following requirements are satisfied.

- [ ] Existing Orbit prototype functionality and design are preserved.
- [ ] Authentication and user-level authorization work correctly.
- [ ] Resume upload, parsing and verification work end-to-end.
- [ ] Job discovery uses authorized, real job sources.
- [ ] Job matching produces explainable scores.
- [ ] Tailored resumes and cover letters are factually grounded.
- [ ] Application tracking persists and validates status changes.
- [ ] LangGraph workflows execute with proper state management.
- [ ] RAG retrieval is scoped and secure.
- [ ] Mock interview feedback works with a documented rubric.
- [ ] Career memory is user-controlled.
- [ ] External actions require explicit human approval.
- [ ] Background processing and reminders are reliable.
- [ ] Security and cross-user isolation tests pass.
- [ ] Unit, integration, API and E2E tests pass.
- [ ] Monitoring, logging and error handling are implemented.
- [ ] Deployment, migration and backup procedures are documented.
- [ ] Known limitations and optional integrations are clearly documented.

---

## 23. Final Engineering Principle

IdeaMate AI should be developed as a reliable software product, not just an AI demonstration.

The priorities should be:

1. Correctness before complexity.
2. Working functionality before additional features.
3. Modularity before code volume.
4. Verified information before AI-generated assumptions.
5. Human control before automation.
6. Security before deployment.
7. Testing before claiming completion.
8. Maintainability before unnecessary optimization.

The final outcome should be a production-oriented, extensible placement co-pilot that can evolve from a student hackathon prototype into a real-world career assistance platform.
