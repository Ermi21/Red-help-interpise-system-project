"""
Creates a user directly in the app database. Needed at least once to
bootstrap the first admin, since there is no public self-signup endpoint
on this internal tool — after that, admins can use POST /api/v1/auth/users.

Usage:
    python scripts/create_admin.py --username admin --email admin@example.com --password "change-me" --role admin
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.auth.password import hash_password  # noqa: E402
from app.database.connection import app_session, get_app_engine  # noqa: E402
from app.models.base import Base  # noqa: E402
from app.models import alert, conversation, metadata, user as user_module  # noqa: E402,F401
from app.repositories.user_repository import UserRepository  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--role", default="admin", choices=["viewer", "analyst", "admin"])
    args = parser.parse_args()

    Base.metadata.create_all(bind=get_app_engine())

    with app_session() as session:
        repo = UserRepository(session)
        if repo.get_by_username(args.username) or repo.get_by_email(args.email):
            print(f"A user with username '{args.username}' or email '{args.email}' already exists. Aborting.")
            return

        repo.add(
            user_module.User(
                username=args.username,
                email=args.email,
                hashed_password=hash_password(args.password),
                role=args.role,
            )
        )
        print(f"Created user '{args.username}' with role '{args.role}'.")


if __name__ == "__main__":
    main()
