from pathlib import Path

import pytest
from peewee import OperationalError, SqliteDatabase
from timetracker.main import app
from timetracker.models import MODELS, Project, Tag, Task
from typer.testing import CliRunner


class TestProject:
    @pytest.fixture(autouse=True)
    def _requests(self, db_path: Path, db: SqliteDatabase, runner: CliRunner) -> None:
        self.db_path = db_path
        self.db = db
        self.runner = runner


    def test_list_default(self) -> None:
        result = self.runner.invoke(app, ["-d", self.db_path, "list", "-r"])

        try:
            with self.db.bind_ctx(MODELS):
                assert Project.select().count() == 1
                assert Task.select().count() == 0
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result.exit_code == 0
        assert "Default" in result.stdout


    def test_delete_with_one_project(self) -> None:
        result = self.runner.invoke(app, ["-d", self.db_path, "delete", "Default"])

        try:
            with self.db.bind_ctx(MODELS):
                assert Project.select().count() == 1
                assert Task.select().count() == 0
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result.exit_code == 1
        assert "There must be at least one project." in result.stdout


    def test_create_new_project(self) -> None:
        result = self.runner.invoke(app, ["-d", self.db_path, "create", "work"])

        try:
            with self.db.bind_ctx(MODELS):
                assert Project.select().count() == 2
                assert Task.select().count() == 0
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result.exit_code == 0
        assert "work" in result.stdout
        assert "created" in result.stdout


    def test_create_duplicate_project(self) -> None:
        result = self.runner.invoke(app, ["-d", self.db_path, "create", "work"])

        try:
            with self.db.bind_ctx(MODELS):
                assert Project.select().count() == 2
                assert Task.select().count() == 0
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result.exit_code == 1
        assert "work" in result.stdout
        assert "does already exist!" in result.stdout


    def test_create_project_with_tag(self) -> None:
        result = self.runner.invoke(app, ["-d", self.db_path, "create", "spare time", "-t", "fun"])

        assert result.exit_code == 0
        try:
            with self.db.bind_ctx(MODELS):
                assert Project.select().count() == 3
                assert Task.select().count() == 0
                assert Tag.select().count() == 1
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert "spare time" in result.stdout
        assert "created" in result.stdout


    def test_list_new_projects(self) -> None:
        result = self.runner.invoke(app, ["-d", self.db_path, "list"])

        try:
            with self.db.bind_ctx(MODELS):
                assert Project.select().count() == 3
                assert Task.select().count() == 0
                assert Tag.select().count() == 1
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result.exit_code == 0
        assert "Default" in result.stdout
        assert "work" in result.stdout
        assert "spare time" in result.stdout
        assert "fun" in result.stdout


    def test_delete_default_project(self) -> None:
        result = self.runner.invoke(app, ["-d", self.db_path, "delete", "Default"])

        try:
            with self.db.bind_ctx(MODELS):
                assert Project.select().count() == 2
                assert Task.select().count() == 0
                assert Tag.select().count() == 1
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result.exit_code == 0
        assert '"Default" has been succesfully deleted!' in result.stdout


    def test_complete_unfinished_project(self) -> None:
        result = self.runner.invoke(app, ["-d", self.db_path, "complete", "work"])

        try:
            with self.db.bind_ctx(MODELS):
                assert Project.select().count() == 2
                assert Task.select().count() == 0
                assert Tag.select().count() == 1
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result.exit_code == 0
        assert "work is now completed" in result.stdout


    def test_complete_already_finished_project(self) -> None:
        result = self.runner.invoke(app, ["-d", self.db_path, "complete", "work"])

        try:
            with self.db.bind_ctx(MODELS):
                assert Project.select().count() == 2
                assert Task.select().count() == 0
                assert Tag.select().count() == 1
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result.exit_code == 1
        assert "work is already completed" in result.stdout


    def test_list_unfinished_projects(self) -> None:
        result = self.runner.invoke(app, ["-d", self.db_path, "list"])

        try:
            with self.db.bind_ctx(MODELS):
                assert Project.select().count() == 2
                assert Task.select().count() == 0
                assert Tag.select().count() == 1
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result.exit_code == 0
        assert "work" not in result.stdout
        assert "spare time" in result.stdout


    def test_list_all_projects(self) -> None:
        result = self.runner.invoke(app, ["-d", self.db_path, "list", "-a"])

        try:
            with self.db.bind_ctx(MODELS):
                assert Project.select().count() == 2
                assert Task.select().count() == 0
                assert Tag.select().count() == 1
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result.exit_code == 0
        assert "work" in result.stdout
        assert "spare time" in result.stdout


    def test_start_task(self) -> None:
        result = self.runner.invoke(
            app, ["-d", self.db_path, "start", "programming", "work", "-t", "testing"]
        )

        try:
            with self.db.bind_ctx(MODELS):
                assert Project.select().count() == 2
                assert Task.select().count() == 1
                assert Tag.select().count() == 2
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result.exit_code == 0
        assert '"programming" has been succesfully started in "work"!' in result.stdout


    def test_cancel_deletion(self) -> None:
        result = self.runner.invoke(app, ["-d", self.db_path, "delete", "work"])

        try:
            with self.db.bind_ctx(MODELS):
                assert Project.select().count() == 2
                assert Task.select().count() == 1
                assert Tag.select().count() == 2
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result.exit_code == 0
        assert "The deletion has been cancelled!" in result.stdout


    def test_confirm_deletion(self) -> None:
        result = self.runner.invoke(app, ["-d", self.db_path, "delete", "work", "-y"])

        try:
            with self.db.bind_ctx(MODELS):
                assert Project.select().count() == 1
                assert Task.select().count() == 0
                assert Tag.select().count() == 1
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result.exit_code == 0
        assert '"work" has been succesfully deleted!' in result.stdout
