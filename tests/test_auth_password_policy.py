import pytest
from conftest import load_service


auth = load_service("auth_service_app", "services/auth_service/app.py")


def test_password_with_six_characters_is_accepted():
    auth.validate_password("123456")


def test_password_with_five_characters_is_rejected():
    with pytest.raises(ValueError, match="al menos 6 caracteres"):
        auth.validate_password("12345")
