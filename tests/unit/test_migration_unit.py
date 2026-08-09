from werkzeug.security import check_password_hash
from conftest import load_service
import pytest

migration = load_service("migration_tool_unit", "services/migration_tool/migrate.py")
pytestmark = pytest.mark.unit


def test_plain_passwords_are_hashed_during_migration():
    hashed = migration.password_hash("secreto123")
    assert hashed != "secreto123"
    assert check_password_hash(hashed, "secreto123")


def test_existing_werkzeug_hash_is_preserved():
    existing = migration.password_hash("secreto123")
    assert migration.password_hash(existing) == existing
