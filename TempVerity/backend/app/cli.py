from __future__ import annotations

import argparse
import getpass

from .auth import reset_password
from .core.config import get_settings
from .db import Base, SessionLocal, engine
from .models import Device, Event, User  # noqa: F401 - register the users table
from .seed import full_capability_demo_device


def reset_password_command(username: str, password: str | None) -> int:
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    new_password = password or getpass.getpass(f"New password for {username}: ")
    confirmation = getpass.getpass("Repeat new password: ") if password is None else new_password
    if new_password != confirmation:
        print("Passwords do not match.")
        return 1
    try:
        with SessionLocal() as session:
            reset_password(session, username, new_password)
    except ValueError as exc:
        print(str(exc))
        return 1
    print(f"Password reset for {username}. Existing sessions were invalidated.")
    return 0


def create_demo_device_command() -> int:
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        demo = full_capability_demo_device()
        if session.get(Device, demo.id) is not None:
            print("Full-capability demo device already exists.")
            return 0
        session.add(demo)
        session.add(Event(device_id=demo.id, kind="device-created", status="active", detail="Full-capability demo device added", created_at=demo.created_at))
        session.commit()
    print("Full-capability two-zone demo device created.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="tempverity")
    commands = parser.add_subparsers(dest="command", required=True)
    reset = commands.add_parser("reset-password", help="Reset an administrator or viewer password")
    reset.add_argument("--username", choices=("administrator", "viewer"), required=True)
    reset.add_argument("--password", help="Password for non-interactive use; omit to securely prompt")
    commands.add_parser("create-demo-device", help="Create a local two-zone device with full demo capabilities")
    args = parser.parse_args()
    if args.command == "reset-password":
        return reset_password_command(args.username, args.password)
    if args.command == "create-demo-device":
        return create_demo_device_command()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
