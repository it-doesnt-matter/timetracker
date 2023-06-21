import re
import zoneinfo
from abc import ABC, abstractmethod
from importlib.resources import files
from typing import Generic, Optional, TypeVar, Any
from zoneinfo import ZoneInfo  # also import tzdata

T = TypeVar("T")


# Setting (SINGULAR) represents a single setting
class Setting(Generic[T], ABC):
    def __init__(self, value: Optional[str] = None) -> None:
        self.value = value or self.default

    @property
    def value(self) -> T:
        return self._value

    @value.setter
    def value(self, value: str) -> None:
        if not self.validate(value):
            raise ValueError

        self._value = self.parse(value)

    @staticmethod
    @abstractmethod
    def name() -> str:
        pass

    @property
    @abstractmethod
    def default(self) -> str:
        pass

    @abstractmethod
    def validate(self, value: str) -> bool:
        pass

    @abstractmethod
    def parse(self, value: str) -> T:
        pass

    @abstractmethod
    def serialize(self) -> str:
        pass


class TZ(Setting[ZoneInfo]):
    @staticmethod
    def name() -> str:
        return "tz"

    @property
    def default(self) -> ZoneInfo:
        return "UTC"

    def validate(self, value: str) -> bool:
        return value in zoneinfo.available_timezones()

    def parse(self, value: str) -> ZoneInfo:
        return ZoneInfo(value)

    def serialize(self) -> str:
        return self._value.key


class Status(Setting[str]):
    @staticmethod
    def name() -> str:
        return "status"

    @property
    def default(self) -> str:
        return "basic"

    def validate(self, value: str) -> bool:
        return value.lower() in ["basic", "b", "fullscreen", "f"]

    def parse(self, value: str) -> str:
        if value.lower() in ["basic", "b"]:
            return "basic"
        elif value.lower() in ["fullscreen", "f"]:
            return "fullscreen"
        else:
            raise ValueError

    def serialize(self) -> str:
        return self._value


class Sections(Setting[str]):
    @staticmethod
    def name() -> str:
        return "sections"

    @property
    def default(self) -> str:
        return "none"

    def validate(self, value: str) -> bool:
        return value.lower() in ["none", "null", "days", "d", "weeks", "w", "months", "m"]

    def parse(self, value: str) -> str:
        if value.lower() in ["none", "null"]:
            return "none"
        elif value.lower() in ["days", "d"]:
            return "days"
        elif value.lower() in ["weeks", "w"]:
            return "weeks"
        elif value.lower() in ["months", "m"]:
            return "months"
        else:
            raise ValueError

    def serialize(self) -> str:
        return self._value


# Settings (PLURAL) represents an object, which handles all operations related to settings
class Settings:
    ALL_SETTINGS = [TZ, Status, Sections]

    def __init__(self) -> None:
        self.set_defaults()

    def set_defaults(self) -> None:
        for setting in self.ALL_SETTINGS:
            setattr(self, setting.name(), setting())

    def set_attribute(self, key: str, value: str) -> None:
        setting = getattr(self, key)
        setting.value = value

    def load_settings(self) -> None:
        try:
            loaded_settings = files("timetracker").joinpath("settings.txt").read_text("utf-8")
        except FileNotFoundError:
            self.set_defaults()
            self.write()
            return

        pattern = re.compile(
            r"tz = (?P<tz>[a-zA-Z][a-zA-Z0-9_\/]*)\n"
            r"status = (?P<status>[a-zA-Z][a-zA-Z0-9_\/]*)\n"
            r"sections = (?P<sections>[a-zA-Z][a-zA-Z0-9_\/]*)"
        )
        match = pattern.fullmatch(loaded_settings)
        if match is None:
            raise ValueError

        for setting in vars(self).values():
            setting.value = match.group(setting.name())

    def write(self) -> None:
        settings_file = files("timetracker").joinpath("settings.txt")
        with settings_file.open("w", encoding="utf-8") as file:
            for index, setting in enumerate(vars(self).values()):
                if index == 0:
                    line = f"{setting.name()} = {setting.serialize()}"
                else:
                    line = f"\n{setting.name()} = {setting.serialize()}"
                file.write(line)

    def show_current_config(self) -> None:
        for setting in vars(self).values():
            print(f"{setting.name()}  =  {setting.value}")

    def validate_setting(self, key: str, value: Any) -> bool:
        setting = getattr(self, key)
        return setting.validate(value)
