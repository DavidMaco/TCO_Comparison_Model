---
applyTo: "**"
---

# Documentation Standards — TCO Comparison Model

## When to Write Documentation

Write or update documentation when:

- Adding a new TCO calculation method or cost factor
- Changing API endpoint schemas
- Modifying environment variable requirements

Do **not** add docstrings or comments to code you did not change.

## Docstring Format (Python)

```python
def compare_tco(options: list[TCOOption], discount_rate: float) -> TCOResult:
    """Compare total cost of ownership across procurement options.

    Args:
        options: List of procurement options to compare.
        discount_rate: Annual discount rate for NPV calculation (0.0–1.0).

    Returns:
        TCOResult with ranked options and cost breakdown.

    Raises:
        ValueError: If options list is empty.
    """
```

## README Updates

Every `README.md` must include:

1. One-sentence product description
2. Quickstart commands
3. Environment variable list

## Changelog

Format: `## [YYYY-MM-DD] — description`.

## Standards Docs Location

Implementation status lives in `docs/`:

- `STANDARDS_IMPLEMENTATION.md`
- `SKILLS_IMPLEMENTATION.md`
- `ROLLOUT_IMPLEMENTATION.md`
