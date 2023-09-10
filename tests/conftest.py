from datetime import datetime
from pathlib import Path

import pytest
from peewee import SqliteDatabase
from timetracker.models import MODELS, Project
from typer.testing import CliRunner


@pytest.fixture(scope="module", autouse=True)
def db_path() -> Path:
    path = Path(__file__).parent.joinpath("fixture.db")
    with path.open("w"):
        pass
    return path


@pytest.fixture(scope="module", autouse=True)
def db(db_path: Path) -> SqliteDatabase:
    db = SqliteDatabase(db_path, pragmas={"foreign_keys": 1})
    with db.bind_ctx(MODELS):
        db.create_tables(MODELS)
        Project.create(name="Default", start=datetime.utcnow())
    return db


@pytest.fixture(scope="module", autouse=True)
def runner() -> CliRunner:
    return CliRunner()
