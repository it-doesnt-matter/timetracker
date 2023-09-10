from pathlib import Path

import pytest
from peewee import OperationalError, SqliteDatabase
from timetracker.main import app
from timetracker.models import MODELS, Project, Tag, Task
from typer.testing import CliRunner


class TestUnusedTag:
    @pytest.fixture(autouse=True)
    def _requests(self, db_path: Path, db: SqliteDatabase, runner: CliRunner) -> None:
        self.db_path = db_path
        self.db = db
        self.runner = runner

    def test_setup(self) -> None:
        result_1 = self.runner.invoke(
            app, ["-d", self.db_path, "create", "work", "-t", "stressful"]
        )
        result_2 = self.runner.invoke(
            app, ["-d", self.db_path, "create", "spare time", "-t", "interesting"]
        )
        result_3 = self.runner.invoke(
            app, ["-d", self.db_path, "start", "programming", "work", "-t", "testing"]
        )

        try:
            with self.db.bind_ctx(MODELS):
                assert Project.select().count() == 3
                assert Task.select().count() == 1
                assert Tag.select().count() == 3
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result_1.exit_code == 0
        assert result_2.exit_code == 0
        assert result_3.exit_code == 0
        assert "work" in result_1.stdout
        assert "created" in result_1.stdout
        assert "spare time" in result_2.stdout
        assert "created" in result_2.stdout
        assert '"programming" has been succesfully started in "work"!' in result_3.stdout


    def test_delete_project(self) -> None:
        result = self.runner.invoke(app, ["-d", self.db_path, "delete", "work", "-y"])

        try:
            with self.db.bind_ctx(MODELS):
                assert Project.select().count() == 2
                assert Task.select().count() == 0
                assert Tag.select().count() == 1
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result.exit_code == 0
        assert '"work" has been succesfully deleted!' in result.stdout
