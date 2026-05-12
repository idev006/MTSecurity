"""
Create or reset the SUPERADMIN account.

Usage (from backend/ directory):
    python scripts/create_admin.py
    python scripts/create_admin.py --username admin --password MyPass123
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Allow running from backend/ dir
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth.password import hash_password
from config import get_settings
from db.init_db import create_tables
from db.session import init_engine
from models.user import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def run(username: str, password: str) -> None:
    cfg = get_settings()
    engine = init_engine(cfg.database_url)
    await create_tables(engine)

    async with AsyncSession(engine) as session:
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        hashed = hash_password(password)

        if user:
            user.hashed_password = hashed
            user.role = "SUPERADMIN"
            user.is_active = True
            print(f"[OK] Password updated for existing user '{username}'")
        else:
            user = User(
                username=username,
                hashed_password=hashed,
                role="SUPERADMIN",
                is_active=True,
                display_name="Administrator",
            )
            session.add(user)
            print(f"[OK] Created SUPERADMIN user '{username}'")

        await session.commit()

    await engine.dispose()
    print(f"     Login at http://localhost:8000/docs or the frontend")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create or reset SUPERADMIN account")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default=None)
    args = parser.parse_args()

    if not args.password:
        import getpass
        while True:
            pw = getpass.getpass("Password (min 8 chars, upper+lower+digit): ")
            pw2 = getpass.getpass("Confirm password: ")
            if pw != pw2:
                print("[ERR] Passwords do not match")
                continue
            from auth.password import validate_policy
            errs = validate_policy(pw)
            if errs:
                print("[ERR]", "; ".join(errs))
                continue
            args.password = pw
            break

    asyncio.run(run(args.username, args.password))
