import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from jobsearch_os import db, migrations, profile, scoring  # noqa: E402


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """Isolated DB + artifacts dir per test; production dirs untouched."""
    monkeypatch.setenv("JOBSEARCH_ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    conn = db.connect(tmp_path / "test.db")
    migrations.migrate(conn)
    profile.seed_facts(conn)
    yield conn
    conn.close()


@pytest.fixture
def rules():
    return scoring.load_rules()


REVOPS_JD = (
    "Own CRM data hygiene in Salesforce, improve lead routing and follow-up, build pipeline "
    "reports in Excel, and document our sales process. 1-3 years experience. SQL a plus. B2B SaaS."
)
