from importlib.resources import files

from peewee import CharField, DateTimeField, ForeignKeyField, Model, SqliteDatabase
from rich.prompt import Confirm

DB_FILE = files("timetracker").joinpath("timetracker.db")
db = SqliteDatabase(DB_FILE, pragmas={"foreign_keys": 1})


class BaseModel(Model):
    class Meta:
        database = db
        legacy_table_names = False


class Project(BaseModel):
    name = CharField(unique=True)


class Task(BaseModel):
    name = CharField()
    note = CharField(null=True)
    start = DateTimeField()
    end = DateTimeField(null=True)
    target = DateTimeField(null=True)
    project = ForeignKeyField(Project, backref="tasks")


MODELS = [Project, Task]


def init_database() -> None:
    try:
        DB_FILE.touch(exist_ok=False)
    except FileExistsError:
        confirmation_text = "This file does already exist. Do you want to overwrite it?"
        if not Confirm.ask(confirmation_text, default=False):
            return

    with DB_FILE.open("w"):
        pass

    with db:
        db.create_tables(MODELS)
        Project.create(name="Default")


if __name__ == "__main__":
    init_database()
