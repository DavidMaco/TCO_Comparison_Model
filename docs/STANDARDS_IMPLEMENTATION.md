# TCO Comparison Model Standards Implementation

## Scope

This document defines implemented standards for this repository.

## Implemented Standards

### 1. Execution Workflow Standard

Implemented via `.github/instructions/execution-workflow.instructions.md`
and `.github/skills/plan-execute-verify/SKILL.md`.

Key rules:

- Plan-first for non-trivial tasks
- Mandatory verification before completion

### 2. FastAPI / API Layer Standard

Implemented via `.github/instructions/api-ops.instructions.md`.

Key rules:

- Pydantic models for all request/response schemas
- No raw exception text in `HTTPException.detail`
- CORS configured via settings, not wildcards

### 3. Streamlit Quality Standard

Implemented via `.github/instructions/frontend-quality.instructions.md`.

Key rules:

- `@st.cache_data` for all data-loading functions
- Empty DataFrame handling before rendering

### 4. Security Review Standard

Implemented via `.github/instructions/security.instructions.md`
and `.github/skills/standards-review/SKILL.md`.

Key rules:

- No hardcoded fallback secrets
- CI-enforced pattern scan

### 5. Documentation Standard

Implemented via `.github/instructions/documentation.instructions.md`.

Key rules:

- Conventional commits, one logical change per commit
