import io
import json
import tarfile
import pytest
import requests
from conftest import wait_for_mail

pytestmark = pytest.mark.integration


def test_notifications_are_logged_and_delivered_to_mailpit(urls, admin_headers, create_user):
    user = create_user("correo")
    message = wait_for_mail(urls, user["email"], "cuenta")
    assert message
    logs = requests.get(f"{urls['notifications']}/api/notifications?recipient={user['email']}", headers=admin_headers, timeout=20)
    assert logs.status_code == 200
    assert any(item["status"] == "sent" for item in logs.json()["items"])


def test_notification_validation_and_admin_listing(urls, admin_headers, internal_key):
    invalid = requests.post(f"{urls['notifications']}/api/notifications", headers={"X-Internal-Key":internal_key}, json={"recipient":"no-es-correo","event_type":"generic","context":{}}, timeout=15)
    assert invalid.status_code == 400
    listing = requests.get(f"{urls['notifications']}/api/notifications?status=sent", headers=admin_headers, timeout=15)
    assert listing.status_code == 200 and listing.json()["total"] >= 1


def test_complete_backup_contains_all_databases_and_manifest(urls, admin_headers):
    response = requests.get(f"{urls['backup']}/api/backups/export", headers=admin_headers, timeout=120)
    assert response.status_code == 200, response.text
    with tarfile.open(fileobj=io.BytesIO(response.content), mode="r:gz") as archive:
        names = set(archive.getnames())
        assert names == {"manifest.json","auth_db.dump","documents_db.dump","catalog_db.dump","notifications_db.dump"}
        manifest = json.load(archive.extractfile("manifest.json"))
    assert manifest["format"] == "actas-microservices-backup-v2"
    assert set(manifest["databases"]) == {"auth_db","documents_db","catalog_db","notifications_db"}


def test_invalid_backup_is_rejected_without_touching_databases(urls, admin_headers):
    response = requests.post(f"{urls['backup']}/api/backups/import", headers=admin_headers, files={"backup":("invalido.tar.gz", b"esto no es un respaldo", "application/gzip")}, timeout=30)
    assert response.status_code == 400
