import argparse
import asyncio
import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionFactory
from app.models import Admin


async def create_admin(username: str, password: str) -> None:
    async with SessionFactory() as session:
        existing = await session.scalar(select(Admin).where(Admin.username == username))
        if existing:
            raise SystemExit(f"Admin {username!r} already exists")
        session.add(Admin(username=username, password_hash=hash_password(password)))
        await session.commit()
    print(f"Admin {username!r} created")


async def set_admin_password(username: str, password: str) -> None:
    async with SessionFactory() as session:
        admin = await session.scalar(select(Admin).where(Admin.username == username))
        if admin is None:
            raise SystemExit(f"Admin {username!r} does not exist")
        admin.password_hash = hash_password(password)
        await session.commit()
    print(f"Password for admin {username!r} updated")


def read_password(provided: str | None) -> str:
    password = provided or getpass.getpass("Password: ")
    if len(password) < 12:
        raise SystemExit("Password must contain at least 12 characters")
    return password


def main() -> None:
    parser = argparse.ArgumentParser(prog="stopcard")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create-admin")
    create.add_argument("username")
    create.add_argument("--password")
    update = subparsers.add_parser("set-admin-password")
    update.add_argument("username")
    update.add_argument("--password")
    args = parser.parse_args()

    if args.command == "create-admin":
        asyncio.run(create_admin(args.username, read_password(args.password)))
    elif args.command == "set-admin-password":
        asyncio.run(set_admin_password(args.username, read_password(args.password)))
