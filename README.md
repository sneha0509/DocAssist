# Overview
This project builds an end-to-end, AI-assisted documentation pipeline that ingests repository metadata from multi-language codebases (Python, PHP, JavaScript, Jupyter notebooks), analyzes it, and generates developer-ready Markdown documentation. It automates the heavy lifting of discovery, structuring, and narration by combining static analysis (AST/regex/Pygments) with Azure OpenAI for high-quality, factual write-ups governed by a strict instruction prompt. The system is designed for accuracy, consistency, and maintainability—favoring metadata-derived facts over speculation and preserving identifiers exactly.

---

## End Result
- Automate documentation creation from real code artifacts to reduce manual effort and improve onboarding.
- Provide consistent, professional Markdown with architecture, APIs, configuration, dependencies, data models, workflows, testing, CI/CD, operational notes, and TODOs.
- Integrate outputs into standard delivery channels (TXT/Markdown/Google Docs) for easy sharing with teams and stakeholders.

---

## Core Components

### 1. Repo Acquisition & Classification
- `download_github_repo(repo_url)`: clones repositories locally.
- Directory walkers identify and segregate code vs non-code files; code files are copied to `working/<repo_name>` for analysis.

### 2. Metadata Extraction
Language-aware analyzers (Python, JS, PHP, ipynb) using ASTs, regex and Pygments capture:
- Modules, classes, functions, signatures, parameters, return types
- Imports/exports, global constants, configuration usage (.env, settings)
- Dependencies (pip/npm/composer), APIs/endpoints, schemas/DTOs
- Notebooks’ cell summaries, inputs/outputs  
**Output:** serialized to `result/metadata.json` (stable, consistent schema).

### 3. Instruction & Prompting
- **System instruction file (`instruction.txt`)**: locks style, format, constraints, and section structure.
- **Developer prompt**: enforces concise, professional Markdown based strictly on provided metadata.
- **User payload**: supplies the metadata JSON for the model to transform.

### 4. Documentation Generation (Azure OpenAI)
- `analyse_metadata()`: constructs chat messages (system/developer/user) and calls Azure OpenAI (`client.chat.completions.create`) with controlled token limits and non-streaming completion.
- Output adheres to a fixed Markdown skeleton:
  - Architecture
  - Modules
  - Public API
  - Config
  - Dependencies
  - Data Models
  - Workflow
  - Notebooks
  - Testing
  - Usage Examples
  - CI/CD
  - Ops
  - Known Issues
  - Glossary

### 5. Publishing & Persistence
- Results written to `result/documentation_output.txt` for traceability.
- Optional Google Docs integration (service account) appends responses to a shared document for collaboration.

---

## Workflow
1. Clone repo → identify code files → move into working directory.
2. Parse code and notebooks → emit normalized metadata JSON.
3. Read `instruction.txt` + developer prompt → call Azure OpenAI with metadata.
4. Receive Markdown completion → persist as TXT/Markdown (and optionally Google Docs).
5. Iterate: missing sections marked as TODOs; known inconsistencies and version conflicts surfaced.

---

## Technology Stack
- **Python**: repository management, classification, metadata extraction, and I/O.
- **Pygments/AST/regex**: static analysis across Python/JS/PHP/ipynb.
- **Azure OpenAI**: Chat Completions API for documentation synthesis under strict prompts.
- **Google Docs API** (optional): publishing to shared documents.
- Standard libraries for file system operations and environment management.

---
