import os
import re
import uuid
import pytest
import requests
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_admin_navigation_is_clear_and_all_modules_open(admin_page, urls):
    page = admin_page
    page.goto(urls["web"] + "/admin")
    expect(page.get_by_role("heading", name=re.compile("Configure el sistema"))).to_be_visible()
    for text, path in [
        ("Dashboard","/admin/dashboard"),
        ("Usuarios y permisos","/admin/usuarios"),
        ("Documentos","/admin/documentos"),
        ("Empresas","/admin/empresas"),
        ("Editor visual de formularios","/admin/campos"),
        ("Notificaciones","/admin/notificaciones"),
        ("Respaldos","/admin/respaldo"),
    ]:
        page.goto(urls["web"] + "/admin")
        module_link = page.locator("main").locator(f"a[href='{path}']").first
        expect(module_link).to_be_visible()
        module_link.click()
        expect(page).to_have_url(re.compile(re.escape(path)))


def test_admin_can_create_user_from_visual_crud(admin_page, urls, run_id, internal_key, admin_user):
    page = admin_page
    email = f"ui.{run_id}.{uuid.uuid4().hex[:5]}@test.local"
    page.goto(urls["web"] + "/admin/usuarios/crear")
    page.locator("#nombre").fill("Usuario creado por interfaz")
    page.locator("#email").fill(email)
    page.locator("#password").fill("123456")
    page.locator("#rol").select_option("usuario")
    page.get_by_role("button", name=re.compile("Crear Usuario", re.I)).click()
    expect(page).to_have_url(re.compile(r"/admin/usuarios"))
    expect(page.get_by_text(email, exact=True)).to_be_visible()
    api = requests.get(f"{urls['auth']}/api/users", headers={"X-Internal-Key":internal_key,"X-User-ID":str(admin_user["id"]),"X-User-Role":"admin"}, timeout=15)
    assert any(x["email"] == email for x in api.json()["items"])


def test_normal_user_cannot_open_admin(normal_user, login_page, urls):
    page = login_page(normal_user["email"], normal_user["password"])
    page.goto(urls["web"] + "/admin")
    expect(page).to_have_url(re.compile(r"/dashboard"))
    expect(page.get_by_text("Acceso denegado.")).to_be_visible()


def test_dashboard_and_configuration_shortcut_are_admin_only(admin_page, normal_user, login_page, urls):
    admin = admin_page
    admin.goto(urls["web"] + "/crear")
    expect(admin.get_by_role("link", name="Configuración")).to_be_visible()
    admin.goto(urls["web"] + "/admin/dashboard")
    expect(admin.get_by_role("heading", name="Dashboard administrativo")).to_be_visible()

    normal = login_page(normal_user["email"], normal_user["password"])
    normal.goto(urls["web"] + "/crear")
    expect(normal.get_by_role("link", name="Configuración")).to_have_count(0)
    expect(normal.locator("a[href='/admin/dashboard']")).to_have_count(0)
    normal.goto(urls["web"] + "/admin/dashboard")
    expect(normal).to_have_url(re.compile(r"/dashboard"))
    expect(normal.get_by_text("Acceso denegado.")).to_be_visible()


def test_admin_can_download_dashboard_as_excel(admin_page, urls):
    page = admin_page
    page.goto(urls["web"] + "/admin/dashboard")
    with page.expect_download() as download_info:
        page.get_by_role("link", name=re.compile("Descargar dashboard", re.I)).click()
    download = download_info.value
    assert download.suggested_filename.startswith("dashboard_administrativo_")
    assert download.suggested_filename.endswith(".xlsx")
