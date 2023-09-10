from pathlib import Path

import pytest
from peewee import OperationalError, SqliteDatabase
from timetracker.main import app
from timetracker.models import MODELS, Project, Task
from typer.testing import CliRunner


class TestEdit:
    @pytest.fixture(autouse=True)
    def _requests(self, db_path: Path, db: SqliteDatabase, runner: CliRunner) -> None:
        self.db_path = db_path
        self.db = db
        self.runner = runner


    def test_create_new_projects(self) -> None:
        result_1 = self.runner.invoke(
            app, ["-d", self.db_path, "create", "work", "-t", "stressful"]
        )
        result_2 = self.runner.invoke(
            app, ["-d", self.db_path, "create", "spare time", "-t", "fun"]
        )

        try:
            with self.db.bind_ctx(MODELS):
                assert Project.select().count() == 3
                assert Task.select().count() == 0
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result_1.exit_code == 0
        assert result_2.exit_code == 0
        assert "work" in result_1.stdout
        assert "created" in result_1.stdout
        assert "spare time" in result_2.stdout
        assert "created" in result_2.stdout


    def test_start_task(self) -> None:
        result = self.runner.invoke(
            app, ["-d", self.db_path, "start", "programming", "work", "-t", "testing"]
        )

        try:
            with self.db:
                assert Project.select().count() == 3
                assert Task.select().count() == 1
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result.exit_code == 0
        assert '"programming" has been succesfully started in "work"!' in result.stdout


    def test_stop_running_task(self) -> None:
        result = self.runner.invoke(app, ["-d", self.db_path, "stop"])

        try:
            with self.db:
                assert Project.select().count() == 3
                assert Task.select().count() == 1
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result.exit_code == 0
        assert '"programming" has been stopped with a run-time of' in result.stdout


    def test_edit_project_name(self) -> None:
        result = self.runner.invoke(app, ["-d", self.db_path, "edit", "p", "work", "name", "job"])

        try:
            with self.db:
                assert Project.select().count() == 3
                assert Task.select().count() == 1
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result.exit_code == 0
        assert "One entry has been updated" in result.stdout


    def test_list_edited_projects(self) -> None:
        result = self.runner.invoke(app, ["-d", self.db_path, "list", "-r"])

        try:
            with self.db:
                assert Project.select().count() == 3
                assert Task.select().count() == 1
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result.exit_code == 0
        assert "Default" in result.stdout
        assert "work" not in result.stdout
        assert "job" in result.stdout
        assert "stressful" in result.stdout
        assert "spare time" in result.stdout
        assert "fun" in result.stdout


    def test_edit_tags(self) -> None:
        result = self.runner.invoke(
            app, ["-d", self.db_path, "edit", "p", "work", "tags", "interesting"]
        )

        try:
            with self.db:
                assert Project.select().count() == 3
                assert Task.select().count() == 1
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result.exit_code == 1
        assert "not yet implemented" in result.stdout
