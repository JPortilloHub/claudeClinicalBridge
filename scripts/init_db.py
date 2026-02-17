#!/usr/bin/env python3
"""Initialize database tables for HITL UI."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Import models first so they register with Base.metadata
from src.python.api.models import User, Workflow, PhaseResult  # noqa: F401
from src.python.utils.database import Base, get_engine, init_tables


def init_db():
    """Create all database tables."""
    print("Creating database tables...")

    try:
        init_tables()
        print("Database tables created successfully!")

        # List created tables
        from sqlalchemy import inspect

        inspector = inspect(get_engine())
        tables = inspector.get_table_names()

        print(f"\nCreated tables ({len(tables)}):")
        for table in sorted(tables):
            print(f"  - {table}")

        print("\nNext step: Run 'python scripts/seed_admin.py' to create default admin user")

    except Exception as e:
        print(f"Error creating tables: {e}")
        sys.exit(1)


if __name__ == "__main__":
    init_db()
