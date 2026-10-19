#!/usr/bin/env python3
"""
Emergency password reset and database migration script.
Run inside the backend container:
  docker exec enterprise-db-rag-backend-backend-1 python scripts/reset_password.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, select
from app.auth.password import hash_password
from app.database.connection import app_session, get_app_engine
from app.models.base import Base
from app.models.user import User

print("Starting DB migration check...")
engine = get_app_engine()
with engine.connect() as conn:
    # Ensure status column in alerts
    try:
        conn.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active'"))
        conn.commit()
        print("Ensured alerts.status column exists.")
    except Exception as e:
        print("Note on alerts.status:", e)

    # Ensure all tables exist from Base.metadata
    try:
        Base.metadata.create_all(bind=engine)
        print("Base.metadata.create_all executed successfully.")
    except Exception as e:
        print("Note on create_all:", e)

USERS_TO_RESET = [
    ("admin", "admin@company.com", "admin123"),
    ("superadmin", "superadmin@company.com", "admin123"),
]

with app_session() as session:
    for username, email, new_password in USERS_TO_RESET:
        user = session.execute(
            select(User).where((User.email == email) | (User.username == username))
        ).scalar_one_or_none()

        if user is None:
            user = User(
                username=username,
                email=email,
                hashed_password=hash_password(new_password),
                role="admin",
                is_active=True,
            )
            session.add(user)
            print(f"Created user: {username} ({email})")
        else:
            user.hashed_password = hash_password(new_password)
            user.is_active = True
            print(f"Reset password for: {username} ({email})")

print("\nAll passwords set to: admin123")
print("Login with:")
print("  Email: superadmin@company.com")
print("  Password: admin123")
