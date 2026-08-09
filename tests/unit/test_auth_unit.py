import pytest
from conftest import load_service

auth = load_service("auth_service_unit", "services/auth_service/app.py")
pytestmark = pytest.mark.unit


def test_password_policy_accepts_six_and_rejects_five():
    auth.validate_password("123456")
    with pytest.raises(ValueError, match="al menos 6"):
        auth.validate_password("12345")


def test_roles_are_strictly_validated():
    assert auth.validate_role("ADMIN") == "admin"
    assert auth.validate_role("usuario") == "usuario"
    with pytest.raises(ValueError, match="Rol inválido"):
        auth.validate_role("superusuario")
