# TCO Comparison Model — Copilot Instructions

Python analytics tool for total cost of ownership comparison across procurement
options. FastAPI backend, Streamlit frontend, analytics pipeline.

## Verification Gates

```bash
ruff check . --config pyproject.toml
black --check --config pyproject.toml .
pytest tests -q        # if tests/ exists
python run_tco_pipeline.py --dry-run 2>/dev/null || python run_tco_pipeline.py
```

## Security Standards (non-negotiable)

- **Never** add `os.environ.get("VAR", "fallback-secret")` — raise `RuntimeError` if missing
- No secrets in source code or `.env` committed to version control
- FastAPI endpoints must not expose raw exception text via `detail=str(exc)`
- CORS must not use `allow_origins=["*"]` in production

## Code Standards

### Python

- `from __future__ import annotations` on every module
- Pydantic models for all FastAPI request/response schemas
- Settings object via `config.py` — no bare `os.environ` in business logic
- Logger via `logging.getLogger(__name__)`

## Instruction Files

| Scope | File |
|---|---|
| FastAPI / API layer | `.github/instructions/api-ops.instructions.md` |
| Streamlit / Output | `.github/instructions/frontend-quality.instructions.md` |
| Security | `.github/instructions/security.instructions.md` |
| Documentation | `.github/instructions/documentation.instructions.md` |
| Workflow | `.github/instructions/execution-workflow.instructions.md` |
