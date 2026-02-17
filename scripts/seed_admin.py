#!/usr/bin/env python3
"""Seed the database with a default admin user."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from passlib.context import CryptContext

# Import models first so they register with Base.metadata
from src.python.api.models import User  # noqa: F401
from src.python.utils.database import SessionLocal, init_tables

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def seed_admin():
    """Create default admin user if it doesn't exist."""
    # Ensure tables exist
    init_tables()

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == "admin").first()
        if existing:
            print("Admin user already exists, skipping.")
            return

        admin = User(
            username="admin",
            hashed_password=pwd_context.hash("admin"),
            full_name="Admin User",
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print("Default admin user created (username: admin, password: admin)")
        print("Change the password after first login!")

    except Exception as e:
        print(f"Error seeding admin: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed_admin()
