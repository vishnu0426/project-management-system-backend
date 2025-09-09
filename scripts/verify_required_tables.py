"""
Verify that all SQLAlchemy-declared tables exist in the configured database.

Usage:
  python -m backend.scripts.verify_required_tables

Behavior:
  - Loads DB URL from environment (DATABASE_URL or POSTGRES_* variables) or app config if importable
  - Dynamically imports all modules in app.models to make sure Base.metadata is populated
  - Compares Base.metadata tables against database inspector.get_table_names()
  - Exits with non-zero status if any expected tables are missing; prints a clear report
"""
from __future__ import annotations

import os
import sys
import pkgutil
import importlib
from typing import List, Set

from sqlalchemy import create_engine, inspect


def _load_settings_url() -> str:
    # Prefer explicit DATABASE_URL if present
    db_url = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI")

    # Compose from POSTGRES_* if needed
    if not db_url and os.getenv("POSTGRES_HOST"):
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        name = os.getenv("POSTGRES_DB", os.getenv("POSTGRES_DATABASE", "app"))
        db_url = f"postgresql://{user}:{password}@{host}:{port}/{name}"

    # Try app.config if available
    if not db_url:
        try:
            from app.config import settings  # type: ignore
            db_url = getattr(settings, "DATABASE_URL", None) or getattr(settings, "database_url", None)
        except Exception:
            pass

    if not db_url:
        raise RuntimeError("DATABASE_URL is not configured. Set DATABASE_URL or POSTGRES_* variables.")

    # If async URL, convert to sync for inspector
    if db_url.startswith("postgresql+asyncpg"):
        db_url = db_url.replace("postgresql+asyncpg", "postgresql", 1)
    return db_url


def _import_all_models() -> None:
    """Import every module in app.models so Base.metadata is fully populated."""
    try:
        import app.models  # noqa: F401
    except Exception as e:
        print(f"WARNING: Could not import app.models package: {e}")
        return

    package = sys.modules.get("app.models")
    if not package or not hasattr(package, "__path__"):
        return

    for module_info in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
        name = module_info.name
        try:
            importlib.import_module(name)
        except Exception as e:
            print(f"WARNING: Failed to import model module {name}: {e}")


def main() -> int:
    db_url = _load_settings_url()

    # Ensure all model modules are imported to populate Base.metadata
    _import_all_models()

    # Now import Base
    try:
        from app.core.database import Base  # type: ignore
    except Exception as e:
        print(f"ERROR: Could not import Base from app.core.database: {e}")
        return 2

    # Collect expected tables from declared metadata
    expected_tables: Set[str] = {t.name for t in Base.metadata.sorted_tables}
    if not expected_tables:
        print("WARNING: No tables found in Base.metadata. Are models imported?")

    # Connect and inspect actual DB
    engine = create_engine(db_url)
    try:
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
    finally:
        engine.dispose()

    missing = sorted(expected_tables - existing_tables)
    extra = sorted(existing_tables - expected_tables)

    print("Database verification report")
    print("-" * 32)
    print(f"DB URL: {db_url}")
    print(f"Expected tables: {len(expected_tables)}")
    print(f"Existing tables: {len(existing_tables)}")

    if missing:
        print("\nMissing tables (expected but not found):")
        for t in missing:
            print(f"  - {t}
")
    else:
        print("\nNo missing tables detected.")

    if extra:
        print("\nExtra tables (present but not declared in models):")
        for t in extra:
            print(f"  - {t}")

    print()
    if missing:
        print("Result: FAIL — some expected tables are missing. Run your migrations/setup.")
        return 1

    print("Result: OK — all expected tables are present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

