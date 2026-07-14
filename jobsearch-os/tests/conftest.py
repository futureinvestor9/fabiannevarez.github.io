import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobsearch import db as jobsearch_db

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def conn(tmp_path):
    connection = jobsearch_db.connect(tmp_path / "test.db")
    jobsearch_db.init_db(connection)
    yield connection
    connection.close()


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")
