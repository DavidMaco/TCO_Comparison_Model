---
applyTo: "**"
---

# Execution Workflow — TCO Comparison Model

The required work pattern for every task in this repository.

## Phase 1 — Understand

1. Read the relevant instruction file for the layer being changed
2. Read files you will modify — understand context before making changes
3. Identify the correct verification gate

## Phase 2 — Plan

Write a step-by-step plan before touching any code.

## Phase 3 — Implement

- Make the smallest change that satisfies the requirement
- Do not refactor or add docstrings to code you didn't change
- Apply security standards throughout

## Phase 4 — Verify

| Layer | Gate |
|---|---|
| Python | `ruff check . && black --check . && pytest tests -q` |
| API | `uvicorn api.main:app --port 8080 &` then `curl localhost:8080/health` |
| Pipeline | `python run_tco_pipeline.py` |
| Streamlit | `streamlit run app.py --server.headless true &` |

## Phase 5 — Validate

- Run `get_errors` on every modified file
- Fix all errors; do not mark a task complete with open errors

## Discipline Rules

- One concern per commit
- Do not add features not in the task scope
