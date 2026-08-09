import re
import time
import pytest
import requests
from conftest import wait_for_mail

pytestmark = pytest.mark.integration


def test_user_crud_login_duplicate_and_password_change(urls, admin_headers, create_user, internal_key):
    user = create_user("crud")
    login = requests.post(f"{urls['auth']}/api/auth/login", headers={"X-Internal-Key":internal_key,"X-Client-IP":"crud-ok"}, json={"email":user["email"],"password":user["password"]}, timeout=15)
    assert login.status_code == 200 and login.json()["rol"] == "usuario"

    duplicate = requests.post(f"{urls['auth']}/api/users", headers=admin_headers, json={"nombre":"Duplicado","email":user["email"],"password":"123456","rol":"usuario"}, timeout=15)
    assert duplicate.status_code == 409

    updated = requests.put(f"{urls['auth']}/api/users/{user['id']}", headers=admin_headers, json={"nombre":"Usuario actualizado","email":user["email"],"password":"NuevaClave2026","rol":"usuario","activo":True}, timeout=15)
    assert updated.status_code == 200, updated.text
    assert updated.json()["session_version"] > user["session_version"]
    old_login = requests.post(f"{urls['auth']}/api/auth/login", headers={"X-Internal-Key":internal_key,"X-Client-IP":"crud-old"}, json={"email":user["email"],"password":user["password"]}, timeout=15)
    new_login = requests.post(f"{urls['auth']}/api/auth/login", headers={"X-Internal-Key":internal_key,"X-Client-IP":"crud-new"}, json={"email":user["email"],"password":"NuevaClave2026"}, timeout=15)
    assert old_login.status_code == 401 and new_login.status_code == 200


def test_six_character_password_is_valid_in_real_api(urls, admin_headers, run_id):
    email = f"six.{run_id}@test.local"
    response = requests.post(f"{urls['auth']}/api/users", headers=admin_headers, json={"nombre":"Seis caracteres","email":email,"password":"123456","rol":"usuario"}, timeout=15)
    assert response.status_code == 201, response.text


def test_login_is_temporarily_blocked_after_five_failures(urls, create_user, internal_key):
    user = create_user("bloqueo")
    headers = {"X-Internal-Key":internal_key,"X-Client-IP":f"lock-{user['id']}"}
    for _ in range(5):
        assert requests.post(f"{urls['auth']}/api/auth/login", headers=headers, json={"email":user["email"],"password":"incorrecta"}, timeout=15).status_code == 401
    blocked = requests.post(f"{urls['auth']}/api/auth/login", headers=headers, json={"email":user["email"],"password":user["password"]}, timeout=15)
    assert blocked.status_code == 429


def test_password_reset_sends_mail_and_token_changes_password(urls, create_user, internal_key):
    user = create_user("recuperacion")
    response = requests.post(f"{urls['auth']}/api/auth/password-reset/request", headers={"X-Internal-Key":internal_key}, json={"email":user["email"]}, timeout=20)
    assert response.status_code == 200
    message = wait_for_mail(urls, user["email"], "contraseña")
    message_id = message.get("ID") or message.get("Id") or message.get("id")
    detail = requests.get(f"{urls['mailpit']}/api/v1/message/{message_id}", timeout=20)
    assert detail.status_code == 200
    body = str(detail.json())
    match = re.search(r"restablecer_contrasena/([A-Za-z0-9_\-]+)", body)
    assert match, body[:1000]
    token = match.group(1)
    assert requests.get(f"{urls['auth']}/api/auth/password-reset/{token}", headers={"X-Internal-Key":internal_key}, timeout=15).status_code == 200
    reset = requests.post(f"{urls['auth']}/api/auth/password-reset/{token}", headers={"X-Internal-Key":internal_key}, json={"password":"Reset2026"}, timeout=15)
    assert reset.status_code == 200, reset.text
    reused = requests.post(f"{urls['auth']}/api/auth/password-reset/{token}", headers={"X-Internal-Key":internal_key}, json={"password":"Otra2026"}, timeout=15)
    assert reused.status_code == 404


def test_last_admin_and_self_deactivation_are_protected(urls, admin_headers, admin_user, create_user):
    second = create_user("adminsecundario", "admin")
    self_delete = requests.delete(f"{urls['auth']}/api/users/{admin_user['id']}", headers=admin_headers, timeout=15)
    assert self_delete.status_code == 409
    delete_second = requests.delete(f"{urls['auth']}/api/users/{second['id']}", headers=admin_headers, timeout=15)
    assert delete_second.status_code == 200 and delete_second.json()["deactivated"] is True
