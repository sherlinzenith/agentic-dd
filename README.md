# Agentic AI Due Diligence Platform

> **An intelligent Due Diligence layer for VDRs — turning documents into evidence, findings, and review-ready insights.**

---

## Why this project?

Due Diligence teams spend significant time reviewing large volumes of financial, legal, and business documents.

The challenge is not simply finding information. A useful Due Diligence system needs to understand **what should be investigated, where the evidence is, what may require attention, and what a reviewer should validate**.

This project explores an **agentic AI approach to Due Diligence** where specialized AI agents investigate different workstreams while maintaining evidence traceability and keeping humans in control of final decisions.

---

## The idea

Instead of treating AI as a simple document chatbot:

```text
Upload Documents
       ↓
      Ask AI
       ↓
     Get Answer
```

the platform follows a structured investigation workflow:

```text
VDR Workspace
      ↓
Document Intelligence
      ↓
Workstream Classification
      ↓
Investigation Planning
      ↓
Specialist AI Agents
      ↓
Evidence Verification
      ↓
Findings & Risks
      ↓
Human Review
      ↓
Approved Findings
      ↓
DD Report
```

The goal is to move from **document searching** to **structured investigation**.

---

## Core Capabilities

### 📄 Document Intelligence

Documents uploaded to a Due Diligence workspace are processed and organized into relevant workstreams.

Current workstreams:

- Financial
- Legal

The architecture is designed to support additional workstreams as the platform evolves.

### 🧠 Investigation Planning

The Due Diligence process begins with an investigation plan that defines the areas to be reviewed.

The planning layer helps turn a broad Due Diligence request into a structured investigation rather than sending every document through the same generic AI process.

### 🤖 Specialist AI Agents

| Agent | Role |
|---|---|
| Lead / Planning Agent | Plans and coordinates the investigation |
| Financial Agent | Performs financial Due Diligence checks |
| Legal Agent | Reviews legal documents and contractual provisions |
| Evidence Verification | Validates findings against supporting evidence |

The workflow is coordinated using **LangGraph**.

### 💰 Financial Due Diligence

The Financial Agent performs automated checks across financial documents, including:

- Income statement analysis
- Revenue checks
- Balance sheet consistency
- Cash flow checks
- Net income consistency
- Financial calculations
- Potential financial findings

The objective is to surface items that deserve reviewer attention rather than replace professional financial judgment.

### ⚖️ Legal Due Diligence

The Legal Agent analyzes contracts and agreements for important provisions and potential issues, including:

- Change of control
- Assignment restrictions
- Termination provisions
- Auto-renewal
- Exclusivity
- Non-compete provisions
- Liability provisions
- Governing law

### 🔎 Evidence Verification

A key principle of the platform is:

> **A finding should be connected to the evidence that supports it.**

The evidence layer helps connect findings to:

- Source document
- Page
- Extracted text
- Relevant values
- Supporting reasoning

This improves traceability and helps reduce unsupported AI conclusions.

### 👤 Human Review

AI-generated findings are not automatically treated as final conclusions.

Reviewers can:

- **Approve**
- **Reject**
- **Request More Evidence**

Reviewer decisions and activity are tracked as part of the workflow.

This keeps the system **AI-assisted rather than AI-dependent**.

### 💬 AI Due Diligence Q&A

The platform provides an AI-powered Q&A layer for asking questions about documents in the current workspace.

```text
User Question
      ↓
Document Retrieval
      ↓
Relevant Evidence
      ↓
AI Analysis
      ↓
Grounded Answer
      ↓
Document / Page Sources
```

The Q&A layer is designed to answer from available workspace evidence and surface supporting document references.

---

## How the system fits together

```text
                         VDR WORKSPACE
                              │
                              ▼
                       DOCUMENT LAYER
                              │
                              ▼
                   DOCUMENT INTELLIGENCE
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
               FINANCIAL              LEGAL
               WORKSPACE             WORKSPACE
                    │                   │
                    └─────────┬─────────┘
                              ▼
                     INVESTIGATION PLAN
                              │
                              ▼
                       DD ORCHESTRATOR
                         /          \
                        ▼            ▼
               FINANCIAL AGENT   LEGAL AGENT
                        \            /
                         ▼          ▼
                       EVIDENCE VERIFICATION
                              │
                              ▼
                           FINDINGS
                              │
                              ▼
                        HUMAN REVIEW
                       /      │       \
                      ▼       ▼        ▼
                  APPROVE   REJECT   MORE EVIDENCE
                      │       │        │
                      └───────┴────────┘
                              │
                              ▼
                      APPROVED FINDINGS
                              │
                              ▼
                           REPORT
```

---

## Technology Stack

| Layer | Technology |
|---|---|
| Application UI | Streamlit |
| Language | Python |
| Agent Orchestration | LangGraph |
| LLM Integration | LangChain |
| AI Model | Qwen |
| Document Processing | PyMuPDF, pypdf |
| Embeddings | Sentence Transformers |
| Vector Search | FAISS |
| API Layer | FastAPI |
| Validation | Pydantic |
| Reporting | ReportLab |
| Testing | Pytest |

---

## Project Structure

```text
agentic-dd/
│
├── agents/              # Specialist agents and intelligence modules
│   ├── lead_agent.py
│   ├── financial_agent.py
│   ├── legal_agent.py
│   ├── evidence_verify.py
│   └── cross_domain.py
│
├── processing/          # Document extraction and classification
├── qa/                  # AI DD Q&A and retrieval
├── findings/            # Findings and review management
├── workflow/            # LangGraph workflow and orchestration
├── tools/               # Agent tools and evidence utilities
├── reports/             # Report generation
├── ui/                  # Application services and UI support
├── tests/               # Automated tests
│
├── streamlit_app.py     # Main application
├── requirements.txt     # Python dependencies
├── README.md            # Project documentation
└── .gitignore           # Git exclusions
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Git
- Required AI model access/configuration

### Clone

```bash
git clone https://github.com/sherlinzenith/agentic-dd.git
cd agentic-dd
```

### Create a virtual environment

Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Install dependencies

```powershell
pip install -r requirements.txt
```

### Run the application

```powershell
streamlit run streamlit_app.py
```

---

## Workspace Isolation

The platform is designed around workspace-level isolation.

Runtime data such as uploaded documents and generated results is kept outside version control.

The following are intentionally excluded from Git:

```text
documents/
results/
workspaces/
.venv/
.env
```

This helps prevent local documents, generated results, virtual environments, and credentials from being committed to the repository.

---

## Design Principles

### Evidence First

AI-generated conclusions should be traceable to supporting document evidence.

### Human in the Loop

Human reviewers remain responsible for approving or rejecting AI-generated findings.

### Specialist Intelligence

Different Due Diligence domains are handled by specialized agents instead of one generic analysis flow.

### Workspace Isolation

Documents, investigations, findings, and results belong to their respective workspace.

### Traceability

Findings should remain connected to their supporting documents, evidence, and reviewer decisions.

### VDR as the Source of Truth

The Due Diligence layer is designed to operate alongside a VDR rather than replace the underlying document repository.

---

## Current Workstreams

### Financial

Financial statement analysis, consistency checks, calculations, and financial findings.

### Legal

Contract and agreement analysis, obligations, restrictions, and important contractual provisions.

---

## Roadmap

The platform is designed to grow into a broader multi-workstream Due Diligence system.

Planned areas include:

- Cross-document intelligence
- Risk and action tracking
- Tax Due Diligence
- Commercial Due Diligence
- HR Due Diligence
- Technology / IT Due Diligence
- Regulatory Due Diligence
- Advanced DD analytics
- Enhanced reporting
- Additional specialist agents
- Deeper VDR integration

---

## Project Vision

The long-term vision is to create an intelligent Due Diligence layer that helps deal teams move through the investigation process more efficiently:

```text
Documents
    ↓
Information
    ↓
Investigation
    ↓
Evidence
    ↓
Findings
    ↓
Human Review
    ↓
Decision
```

The objective is not simply to build an AI-powered document search tool.

It is to build a structured **agentic Due Diligence workflow** where AI can help investigate, verify, surface findings, and support deal teams while maintaining evidence traceability and human oversight.

---

## Project Status

This repository represents an actively developed Due Diligence AI platform and proof-of-concept implementation.

The current implementation focuses on:

- Financial Due Diligence
- Legal Due Diligence
- Agentic workflow orchestration
- Evidence verification
- Human review
- Workspace isolation
- AI Due Diligence Q&A
- Reporting and activity tracking

The architecture is intended to evolve toward a broader production-grade VDR-integrated Due Diligence platform.

---

## Repository

**GitHub:**  
https://github.com/sherlinzenith/agentic-dd
w