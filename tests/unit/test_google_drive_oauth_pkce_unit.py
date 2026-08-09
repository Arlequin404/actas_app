from pathlib import Path


def test_google_drive_pkce_verifier_is_persisted_and_reused():
    source = Path("services/backup_service/app.py").read_text(encoding="utf-8")
    assert 'code_verifier = secrets.token_urlsafe(64)' in source
    assert '"code_verifier": code_verifier' in source
    assert 'code_verifier=code_verifier' in source
    assert 'autogenerate_code_verifier=False' in source
    assert 'pending.get("code_verifier")' in source


def test_stale_pre_v17_oauth_attempt_requires_clean_reconnect():
    source = Path("services/backup_service/app.py").read_text(encoding="utf-8")
    assert "fue iniciada con una versión anterior" in source
    assert "GOOGLE_DRIVE_OAUTH_STATE_FILE.unlink(missing_ok=True)" in source
