from conftest import ROOT, load_service

backup = load_service("backup_service_legacy_unit", "services/backup_service/app.py")


def test_pg17_plain_sql_is_normalized_for_postgresql_16():
    source = """-- PostgreSQL database dump\n\\restrict abc123\nSET statement_timeout = 0;\nSET transaction_timeout = 0;\nCREATE TABLE public.usuarios(id integer);\n\\unrestrict abc123\n"""
    result = backup.normalize_legacy_sql_text(source)
    assert "\\restrict" not in result
    assert "\\unrestrict" not in result
    assert "transaction_timeout" not in result
    assert "SET statement_timeout = 0;" in result
    assert "CREATE TABLE public.usuarios" in result


def test_sql_without_pg_dump_header_is_rejected():
    try:
        backup.normalize_legacy_sql_text("DROP DATABASE postgres;")
    except ValueError as exc:
        assert "no parece un respaldo" in str(exc)
    else:
        raise AssertionError("Se aceptó un SQL arbitrario")


def test_backup_page_accepts_current_and_legacy_formats():
    template = (ROOT / "services/web_gateway/templates/admin_respaldo.html").read_text(encoding="utf-8")
    assert ".tar.gz" in template
    assert ".sql" in template
    assert "migran automáticamente" in template


def test_arbitrary_psql_meta_commands_are_rejected():
    source = "-- PostgreSQL database dump\n\\! touch /tmp/no-debe-ejecutarse\n"
    try:
        backup.normalize_legacy_sql_text(source)
    except ValueError as exc:
        assert "comando psql no permitido" in str(exc)
    else:
        raise AssertionError("Se aceptó un metacomando peligroso")


def test_backup_page_keeps_four_backup_actions_separate():
    template = (ROOT / "services/web_gateway/templates/admin_respaldo.html").read_text(encoding="utf-8")
    download = template.index('id="backup-download-card"')
    upload = template.index('id="backup-upload-card"')
    manual = template.index('id="backup-google-drive-manual-card"')
    automatic = template.index('id="backup-google-drive-auto-card"')
    assert download < upload < manual < automatic
    assert 'id="btn-download-backup"' in template
    assert 'id="btn-upload-backup"' in template
    assert 'id="btn-google-drive-manual"' in template
    manual_section = template[manual:automatic]
    automatic_section = template[automatic:]
    assert "respaldo_google_drive_ahora" in manual_section
    assert "respaldo_google_drive_ahora" not in automatic_section


def test_google_drive_backup_uses_cloud_api_not_local_sync_folder():
    template = (ROOT / "services/web_gateway/templates/admin_respaldo.html").read_text(encoding="utf-8")
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    backup_app = (ROOT / "services/backup_service/app.py").read_text(encoding="utf-8")
    assert "Conectar mi Google Drive" in template
    assert "GOOGLE_DRIVE_CLIENT_ID" in compose
    assert "GOOGLE_DRIVE_CLIENT_SECRET" in compose
    assert "GOOGLE_DRIVE_HOST_PATH" not in compose
    assert "googleapiclient" in backup_app
    assert "MediaFileUpload" in backup_app
    assert "files().create" in backup_app
