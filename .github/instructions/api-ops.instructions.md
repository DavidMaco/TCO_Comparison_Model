---
applyTo: "api/**"
---

# FastAPI Standards — TCO Comparison Model

Standards for the API layer (`api/`).

## Route Conventions

- All routes prefixed with `/api/v1/`
- Request/response types use Pydantic models — no raw dicts
- Return typed responses; use `response_model=` on all routes

## Error Handling

```python
# CORRECT
try:
    result = compare_tco(options)
except Exception as exc:
    logger.error("TCO comparison failed", extra={"error": str(exc)})
    raise HTTPException(status_code=500, detail="TCO comparison failed") from exc

# FORBIDDEN
raise HTTPException(status_code=500, detail=str(exc))
```

## CORS

```python
# CORRECT
app.add_middleware(CORSMiddleware, allow_origins=settings.ALLOWED_ORIGINS)

# FORBIDDEN
app.add_middleware(CORSMiddleware, allow_origins=["*"])
```

## Startup

```python
@app.on_event("startup")
async def startup() -> None:
    """Validate required environment variables before accepting requests."""
    required = ["DATABASE_URL", "SECRET_KEY"]
    for var in required:
        if not os.environ.get(var):
            raise RuntimeError(f"{var} must be set")
```
