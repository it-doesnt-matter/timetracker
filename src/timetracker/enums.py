from enum import Enum


class DisplayType(str, Enum):
    basic = "basic"
    b = "b"
    table = "table"
    t = "t"
    fullscreen = "fullscreen"
    f = "f"
    raw = "raw"
    r = "r"


class FileType(str, Enum):
    json = "json"
    csv = "csv"


class TableType(str, Enum):
    task = "task"
    t = "t"
    project = "project"
    p = "p"
