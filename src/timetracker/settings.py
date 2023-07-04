from typing import Literal
from zoneinfo import ZoneInfo  # also import tzdata

from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field, FieldValidationInfo, field_serializer, field_validator


class BaseModel(PydanticBaseModel):
    class Config:
        arbitrary_types_allowed = True
        extra = "forbid"
        validate_assignment = True


class Column(BaseModel):
    attribute: Literal["project", "task", "note", "start", "end", "target", "duration", "id"]
    header_name: str | None = Field(default=None, validate_default=True)
    options: dict[str, str] = {}

    @field_validator("header_name", mode="before")
    def default_header_name(cls, value: str, info: FieldValidationInfo) -> str:
        if "attribute" in info.data:
            return value or info.data["attribute"].upper().replace("_", " ")
        else:
            return ""


class Settings(BaseModel):
    tz: ZoneInfo = ZoneInfo("UTC")
    status: Literal["basic", "table", "fullscreen"] = "basic"
    sections: Literal["none", "days", "weeks", "months"] = "none"
    show_total: bool = False
    recap_layout: list[Column] = [
        Column(attribute="project"),
        Column(attribute="task"),
        Column(attribute="note"),
        Column(attribute="start"),
        Column(attribute="end"),
        Column(attribute="target"),
        Column(attribute="duration"),
    ]

    @field_validator("tz", mode="before")
    def parse_tz(cls, value: str) -> ZoneInfo:
        return ZoneInfo(value)

    @field_validator("status", mode="before")
    def parse_status(cls, value: str) -> str:
        match value.lower():
            case "basic" | "b":
                return "basic"
            case "table" | "t":
                return "table"
            case "fullscreen" | "f":
                return "fullscreen"
            case _:
                raise ValueError

    @field_validator("sections", mode="before")
    def parse_sections(cls, value: str) -> str:
        match value.lower():
            case "none" | "null" | "n":
                return "none"
            case "days" | "d":
                return "days"
            case "weeks" | "w":
                return "weeks"
            case "months" | "m":
                return "months"
            case _:
                raise ValueError

    @field_serializer("tz")
    def serialize_tz(self, tz: ZoneInfo) -> str:
        return tz.key
