from pathlib import Path
import sys
import os


ROOT_DIR = Path(__file__).resolve().parents[1]
TEST_DB_PATH = ROOT_DIR / ".pytest-gateway.db"

os.environ["GATEWAY_DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine

get_settings.cache_clear()


@pytest.fixture(autouse=True)
def reset_test_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
