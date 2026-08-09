import pytest

pytestmark = pytest.mark.integration


def test_required_tables_columns_indexes_and_jsonb_types(auth_db, document_db, catalog_db, notification_db):
    expectations = [
        (auth_db, {"usuarios","password_resets","login_attempts","audit_log"}),
        (document_db, {"documents","document_counters","audit_log"}),
        (catalog_db, {"catalogos","form_sections","form_fields","form_shortcuts","form_settings"}),
        (notification_db, {"notification_log"}),
    ]
    for db, required in expectations:
        with db.cursor() as cur:
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
            assert required.issubset({row[0] for row in cur.fetchall()})
    with document_db.cursor() as cur:
        cur.execute("SELECT data_type FROM information_schema.columns WHERE table_name='documents' AND column_name='extra_data'")
        assert cur.fetchone()[0] == "jsonb"
        cur.execute("SELECT indexname FROM pg_indexes WHERE tablename='documents'")
        indexes = {row[0] for row in cur.fetchall()}
        assert any("code" in name for name in indexes)
    with catalog_db.cursor() as cur:
        cur.execute("SELECT data_type FROM information_schema.columns WHERE table_name='form_fields' AND column_name='options'")
        assert cur.fetchone()[0] == "jsonb"
