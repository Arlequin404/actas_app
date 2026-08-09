import re
import pytest
import requests
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_backup_can_be_downloaded_from_admin_page(admin_page, urls):
    page=admin_page
    page.goto(urls["web"]+"/admin/respaldo")
    link=page.locator("a[href*='/admin/respaldo/exportar']")
    expect(link).to_be_visible()
    with page.expect_download(timeout=120000) as download_info:
        link.click()
    download=download_info.value
    assert download.suggested_filename.endswith(".tar.gz")


def test_document_content_is_rendered_as_text_not_executed_script(admin_page, urls, admin_headers, base_document_payload):
    payload=dict(base_document_payload)
    payload["asunto"]="<script>window.__xss_test=1</script>"
    response=requests.post(f"{urls['documents']}/api/documents/actas",headers=admin_headers,json=payload,timeout=20)
    assert response.status_code==201
    page=admin_page
    page.goto(urls["web"]+"/admin/documentos?tab=actas&per_page=all")
    assert page.evaluate("window.__xss_test || 0") == 0
    expect(page.get_by_text("<script>window.__xss_test=1</script>", exact=True)).to_be_visible()
