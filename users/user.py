"""User data model and simple JSON-based storage."""

from dataclasses import asdict, dataclass
import json
from pathlib import Path


USERS_FILE = Path(__file__).with_name("users.json")


@dataclass
class User:
    first_name: str
    last_initial: str
    user_id: str
    email: str
    zip_code: str
    birthday: str


def load_users() -> list[User]:
    """Return all saved users, or an empty list before any have been saved."""
    if not USERS_FILE.exists():
        return []

    records = json.loads(USERS_FILE.read_text(encoding="utf-8"))
    return [User(**record) for record in records]


def save_users(users: list[User]) -> None:
    """Save the supplied users to the JSON storage file."""
    records = [asdict(user) for user in users]
    USERS_FILE.write_text(json.dumps(records, indent=2), encoding="utf-8")


def add_user(new_user: User) -> None:
    """Save a new user, rejecting a duplicate user ID."""
    users = load_users()

    if any(user.user_id == new_user.user_id for user in users):
        raise ValueError(f"User ID already exists: {new_user.user_id}")

    users.append(new_user)
    save_users(users)
