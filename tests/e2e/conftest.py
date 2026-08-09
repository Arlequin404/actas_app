import re
import pytest
from playwright.sync_api import expect


@pytest.fixture
def login_page(page, urls):
    def _login(email, password):
        page.goto(urls["web"] + "/")
        page.locator("#email").fill(email)
        page.locator("#password").fill(password)
        page.get_by_role("button", name=re.compile("INGRESAR", re.I)).click()
        expect(page).to_have_url(re.compile(r"/dashboard"))
        return page
    return _login


@pytest.fixture
def admin_page(login_page):
    import os
    return login_page(os.environ["ADMIN_EMAIL"], os.environ["ADMIN_PASSWORD"])


@pytest.fixture
def normal_page(login_page, normal_user):
    return login_page(normal_user["email"], normal_user["password"])



def choose_first(select_locator):
    """Selecciona la primera opción con valor real de un <select>."""
    options = select_locator.locator("option")
    for index in range(options.count()):
        value = options.nth(index).get_attribute("value") or ""
        if value:
            select_locator.select_option(index=index)
            return value
    raise AssertionError("No hay opciones seleccionables")
