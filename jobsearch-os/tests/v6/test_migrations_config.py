"""Migration contract + config precedence (Phase-1-blocking, Section U)."""
import pytest

from jobsearch_os import db, migrations
from jobsearch_os.config import Config


def test_migrations_apply_and_record(tmp_path):
    conn = db.connect(tmp_path / "m.db")
    applied = migrations.migrate(conn)
    assert "0001_core" in applied and "0002_phase1_facts" in applied
    # re-running applies nothing
    assert migrations.migrate(conn) == []
    reg = migrations.applied_migrations(conn)
    assert set(reg) >= {"0001_core", "0002_phase1_facts"}


def test_migration_checksum_refusal(tmp_path):
    conn = db.connect(tmp_path / "m.db")
    migrations.migrate(conn)
    conn.execute("UPDATE schema_migrations SET checksum='tampered' WHERE migration_id='0001_core'")
    with pytest.raises(migrations.MigrationChecksumMismatch):
        migrations.migrate(conn)


def test_pragmas_enforced(tmp_path):
    conn = db.connect(tmp_path / "p.db")
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    assert conn.execute("PRAGMA busy_timeout").fetchone()[0] >= 5000


def test_config_precedence(tmp_path, monkeypatch):
    conn = db.connect(tmp_path / "c.db")
    migrations.migrate(conn)
    conn.execute("INSERT INTO settings (key, value) VALUES ('budget_mode', 'critical')")
    cfg = Config(conn=conn, yaml_values={})
    # 4. db settings beats default
    assert cfg.get("budget_mode") == "critical"
    # 3. yaml beats db
    cfg2 = Config(conn=conn, yaml_values={"budget_mode": "conserve"})
    assert cfg2.get("budget_mode") == "conserve"
    # 2. env beats yaml
    monkeypatch.setenv("JOBSEARCH_BUDGET_MODE", "ai_paused")
    assert cfg2.get("budget_mode") == "ai_paused"
    # 1. cli beats all
    assert cfg2.get("budget_mode", cli="normal") == "normal"
