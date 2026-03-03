"""
TCO Comparison Model — Database Utilities
"""
from __future__ import annotations

import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

import config


_engine: Engine | None = None


def get_engine() -> Engine:
    """Return a shared SQLAlchemy engine (singleton)."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            config.DATABASE_URL,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            echo=False,
        )
    return _engine


def health_check() -> bool:
    """Verify database connectivity."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
