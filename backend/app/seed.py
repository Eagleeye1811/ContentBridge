"""Create demo accounts: `python -m app.seed`."""

import asyncio

from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from app.security import hash_password

DEMO_USERS = [
    ("editor@contentbridge.io", "Editor", "editor"),
    ("approver@contentbridge.io", "Approver", "approver"),
]
DEMO_PASSWORD = "contentbridge"


async def main() -> None:
    async with SessionLocal() as db:
        for email, name, role in DEMO_USERS:
            if await db.scalar(select(User).where(User.email == email)):
                print(f"  = {email} already exists")
                continue
            db.add(
                User(
                    email=email,
                    name=name,
                    role=role,
                    password_hash=hash_password(DEMO_PASSWORD),
                )
            )
            print(f"  + {email} ({role})")
        await db.commit()
    print(f"\nPassword for both: {DEMO_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(main())
