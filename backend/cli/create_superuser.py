"""CLI command to bootstrap the initial administrative superuser."""

import asyncio
import sys
from sqlalchemy import select

from backend.auth.schemas import UserCreate
from backend.auth.service import AuthService
from backend.config.settings import get_settings
from backend.database import session as db_session
from backend.models.user import User


async def create_superuser() -> None:
    """Bootstrap the initial superuser account in the database."""
    settings = get_settings()

    # Initialize database engine pool
    db_session.init_engine(settings.postgres)

    if db_session.AsyncSessionLocal is None:
        print("Error: Database engine not initialized.", file=sys.stderr)
        sys.exit(1)

    email = "admin@example.com"
    password = "Admin@123456"

    async with db_session.AsyncSessionLocal() as session:
        try:
            # Check if user already exists
            stmt = select(User).where(User.email == email)
            result = await session.execute(stmt)
            existing_user = result.scalar_one_or_none()

            if existing_user:
                print(f"Skipping: Superuser with email '{email}' already exists.")
                return

            # Bootstrap the superuser
            auth_service = AuthService(session)
            user_data = UserCreate(
                email=email,
                password=password,
                full_name="System Administrator",
                is_superuser=True,
            )

            new_user = await auth_service.create_user(user_data)
            await session.commit()

            print("==================================================")
            print("🚀 Superuser Bootstrapped Successfully!")
            print("==================================================")
            print(f"Email:    {new_user.email}")
            print(f"Password: {password}")
            print("is_active: True")
            print("is_superuser: True")
            print("==================================================")

        except Exception as exc:
            await session.rollback()
            print(f"Error creating superuser: {exc}", file=sys.stderr)
            sys.exit(1)
        finally:
            await db_session.dispose_engine()


if __name__ == "__main__":
    asyncio.run(create_superuser())
