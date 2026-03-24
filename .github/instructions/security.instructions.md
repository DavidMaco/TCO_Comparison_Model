---
applyTo: "**"
---

# Security Standards — TCO Comparison Model

Non-negotiable security requirements. Violations fail the CI `standards-governance` scan.

## Secret Management

```python
# ALWAYS — fail loudly at startup
secret = os.environ.get("API_KEY")
if not secret:
    raise RuntimeError("API_KEY environment variable must be set")

# NEVER — hardcoded fallback
secret = os.environ.get("API_KEY", "dev-key")  # FORBIDDEN
```

- Rotate secrets via environment; never in source code
- No `.env` files committed; add to `.gitignore`

## FastAPI Security

```python
# FORBIDDEN
raise HTTPException(status_code=500, detail=str(exc))

# CORRECT
logger.error("TCO calculation failed", extra={"error": str(exc)})
raise HTTPException(status_code=500, detail="Internal server error")
```

## CORS

```python
# FORBIDDEN
CORSMiddleware(app, allow_origins=["*"])

# CORRECT
CORSMiddleware(app, allow_origins=[settings.ALLOWED_ORIGINS])
```

## CI Enforcement

The `standards-governance` job runs a security pattern scan that will **fail the build** on:

1. `os.environ.get(VAR, "secret-fallback")` patterns
2. `raise HTTPException(..., detail=str(exc))` patterns
3. `allow_origins=["*"]` patterns
