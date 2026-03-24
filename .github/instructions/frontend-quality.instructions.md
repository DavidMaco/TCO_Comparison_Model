---
applyTo: "{app.py,pages/**,streamlit_app.py}"
---

# Streamlit Quality Standards — TCO Comparison Model

## App Conventions

- One `st.set_page_config()` per app entry point only
- Do not call `st.set_page_config()` in page files under `pages/`
- Use `@st.cache_data` for all data-loading functions
- Never embed secrets in source; use `st.secrets` or env vars

## Data Safety

- Handle empty DataFrames before passing to `st.dataframe()` or chart functions
- Validate external inputs (query params, uploaded files) at boundary

## State Management

- Prefer `st.session_state` over module-level mutable shared state
- Clear session state keys that are no longer valid (e.g., on filter change)

## Shared Rules

- No hardcoded file paths — use config or relative paths from project root
- No commented-out code in committed files
