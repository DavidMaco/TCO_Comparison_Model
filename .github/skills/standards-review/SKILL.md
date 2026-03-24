---
name: standards-review
description: Use when reviewing proposed or completed changes for compliance with repository standards, quality gates, security rules, and documentation requirements.
---

# Standards Review

## Objective

Evaluate changes against repository standards and produce actionable findings.

## Review Dimensions

1. Execution workflow compliance
2. Verification evidence quality
3. FastAPI standards and data layer standards
4. Security checklist
5. Streamlit / output quality standards
6. Documentation and commit message standards
7. Scope control

## Output Format

### Standards Review Report

- Status: pass or fail
- Security verdict: CRITICAL / HIGH / MEDIUM / LOW / N/A
- Findings by severity
- Evidence references
- Required fixes
- Advisory improvements

## Rules

- Findings must be concrete and testable.
- Any CRITICAL security item is an automatic FAIL.
- Mark security items as N/A when they do not apply.
