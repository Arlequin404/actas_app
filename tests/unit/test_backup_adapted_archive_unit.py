from pathlib import Path


def test_adapted_tar_archive_support_is_present():
    source = Path("services/backup_service/app.py").read_text(encoding="utf-8")
    assert 'actas-adapted-sql-backup-v1' in source
    assert 'adapted.sql' in source
    assert 'hashlib.sha256' in source
    assert 'restore_safety_dumps' in source
