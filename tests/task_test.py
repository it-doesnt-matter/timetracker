from pathlib import Path

import pytest
from freezegun import freeze_time
from peewee import OperationalError, SqliteDatabase
from timetracker.main import app
from timetracker.models import MODELS, Project, Task
from typer.testing import CliRunner


class TestTask:
    @pytest.fixture(autouse=True)
    def _requests(self, db_path: Path, db: SqliteDatabase, runner: CliRunner) -> None:
        self.db_path = db_path
        self.db = db
        self.runner = runner


    @freeze_time("2020-01-01 12:00:00")
    def test_get_status_with_no_task_running(self) -> None:
        result = self.runner.invoke(app, ["-d", self.db_path, "status"])

        try:
            with self.db:
                assert Project.select().count() == 1
                assert Task.select().count() == 0
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result.exit_code == 1
        assert "There's currently no task running!" in result.stdout


    @freeze_time("2020-01-01 12:01:00")
    def test_start_task_on_nonexistant_project(self) -> None:
        result = self.runner.invoke(app, ["-d", self.db_path, "start", "test", "work"])

        try:
            with self.db:
                assert Project.select().count() == 1
                assert Task.select().count() == 0
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result.exit_code == 1
        assert 'A project, named "work", does not exist!' in result.stdout


    @freeze_time("2020-01-01 12:02:00")
    def test_create_new_projectr(self) -> None:
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


    @freeze_time("2020-01-01 12:03:00")
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


    @freeze_time("2020-01-01 12:04:00")
    def test_get_status(self) -> None:
        result = self.runner.invoke(app, ["-d", self.db_path, "status", "-d", "raw"])

        try:
            with self.db:
                assert Project.select().count() == 3
                assert Task.select().count() == 1
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result.exit_code == 0
        assert "work > programming" in result.stdout


    @freeze_time("2020-01-01 12:05:00")
    def test_start_task_while_other_task_is_running(self) -> None:
        result = self.runner.invoke(app, ["-d", self.db_path, "start", "meeting", "work"])

        try:
            with self.db:
                assert Project.select().count() == 3
                assert Task.select().count() == 1
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result.exit_code == 1
        assert 'There\'s already an ongoing task, called "programming"!' in result.stdout


    @freeze_time("2020-01-01 12:06:00")
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


    @freeze_time("2020-01-01 12:07:00")
    def test_stop_without_running_task(self) -> None:
        result = self.runner.invoke(app, ["-d", self.db_path, "stop"])

        try:
            with self.db:
                assert Project.select().count() == 3
                assert Task.select().count() == 1
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result.exit_code == 1
        assert "There's currently no task running!" in result.stdout


    @freeze_time("2020-01-01 12:08:00")
    def test_start_task_with_for_target(self) -> None:
        result = self.runner.invoke(
            app, ["-d", self.db_path, "start", "running", "spare time", "-f", "1:30"]
        )

        try:
            with self.db:
                assert Project.select().count() == 3
                assert Task.select().count() == 2
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result.exit_code == 0
        assert '"running" has been succesfully started in "spare time"!' in result.stdout


    @freeze_time("2020-01-01 12:09:00")
    def test_get_status_with_for_target(self) -> None:
        result = self.runner.invoke(app, ["-d", self.db_path, "status", "-d", "r"])

        try:
            with self.db:
                assert Project.select().count() == 3
                assert Task.select().count() == 2
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result.exit_code == 0
        assert "spare time > running" in result.stdout
        assert "the target is reached in 01:29:00" in result.stdout


    @freeze_time("2020-01-01 12:10:00")
    def test_stop_task_before_reaching_target(self) -> None:
        result = self.runner.invoke(app, ["-d", self.db_path, "stop"])

        try:
            with self.db:
                assert Project.select().count() == 3
                assert Task.select().count() == 2
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result.exit_code == 0
        assert '"running" has been stopped with a run-time of 00:02:00' in result.stdout
        assert "It would have taken another 01:28:00 to reach the target." in result.stdout


    @freeze_time("2020-01-01 12:11:00")
    def test_start_task_with_until_target(self) -> None:
        result = self.runner.invoke(
            app, ["-d", self.db_path, "start", "cycling", "spare time", "-u", "13:11"]
        )

        try:
            with self.db:
                assert Project.select().count() == 3
                assert Task.select().count() == 3
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result.exit_code == 0
        assert '"cycling" has been succesfully started in "spare time"!' in result.stdout


    @freeze_time("2020-01-01 12:12:00")
    def test_get_status_with_until_target(self) -> None:
        result = self.runner.invoke(app, ["-d", self.db_path, "status", "-d", "r"])

        try:
            with self.db:
                assert Project.select().count() == 3
                assert Task.select().count() == 3
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result.exit_code == 0
        assert "spare time > cycling" in result.stdout
        assert "the target is reached in 00:59:00" in result.stdout


    @freeze_time("2020-01-01 13:20:00")
    def test_stop_task_after_reaching_target(self) -> None:
        result = self.runner.invoke(app, ["-d", self.db_path, "stop"])

        try:
            with self.db:
                assert Project.select().count() == 3
                assert Task.select().count() == 3
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

        assert result.exit_code == 0
        assert '"cycling" has been stopped with a run-time of 01:09:00' in result.stdout
        assert "The target has been reached 00:09:00 ago." in result.stdout
