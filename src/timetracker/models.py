from importlib.resources import files

from peewee import CharField, DateTimeField, ForeignKeyField, Model, SqliteDatabase

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
    project = ForeignKeyField(Project, backref="tasks")


MODELS = [Project, Task]


def init_database() -> None:
    with DB_FILE.open("w"):
        pass

    with db:
        db.create_tables(MODELS)
        Project.create(name="Default")


if __name__ == "__main__":
    init_database()
