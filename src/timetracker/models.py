from datetime import datetime
from importlib.resources import files

from peewee import CharField, CompositeKey, DateTimeField, ForeignKeyField, Model, SqliteDatabase
from rich.prompt import Confirm

DB_FILE = files("timetracker").joinpath("timetracker.db")
db = SqliteDatabase(None, pragmas={"foreign_keys": 1})


class BaseModel(Model):
    class Meta:
        database = db
        legacy_table_names = False


class Project(BaseModel):
    name = CharField(unique=True)
    start = DateTimeField()
    end = DateTimeField(null=True)


class Task(BaseModel):
    name = CharField()
    note = CharField(null=True)
    start = DateTimeField()
    end = DateTimeField(null=True)
    target = DateTimeField(null=True)
    project = ForeignKeyField(Project, backref="tasks")


class Tag(BaseModel):
    name = CharField(unique=True)


class TaskToTag(BaseModel):
    task = ForeignKeyField(Task)
    tag = ForeignKeyField(Tag)

    class Meta:
        primary_key = CompositeKey("task", "tag")


class ProjectToTag(BaseModel):
    project = ForeignKeyField(Project)
    tag = ForeignKeyField(Tag)

    class Meta:
        primary_key = CompositeKey("project", "tag")


MODELS = [Project, Task, Tag, TaskToTag, ProjectToTag]


def init_database() -> None:
    try:
        DB_FILE.touch(exist_ok=False)
    except FileExistsError:
        confirmation_text = "This file does already exist. Do you want to overwrite it?"
        if not Confirm.ask(confirmation_text, default=False):
            return

    with DB_FILE.open("w"):
        pass

    db.init(DB_FILE, pragmas={"foreign_keys": 1})
    with db:
        db.create_tables(MODELS)
        Project.create(name="Default", start=datetime.utcnow())


if __name__ == "__main__":
    init_database()
