import re
from datetime import datetime
from zoneinfo import ZoneInfo

DAYS_IN_SECONDS = 60 * 60 * 24
YEARS_IN_SECONDS = DAYS_IN_SECONDS * 365.25
NUMBERS = [
    "████████\n██    ██\n██    ██\n██    ██\n██    ██\n██    ██\n████████",
    "      ██\n      ██\n      ██\n      ██\n      ██\n      ██\n      ██",
    "████████\n      ██\n      ██\n████████\n██      \n██      \n████████",
    "████████\n      ██\n      ██\n████████\n      ██\n      ██\n████████",
    "██    ██\n██    ██\n██    ██\n████████\n      ██\n      ██\n      ██",
    "████████\n██      \n██      \n████████\n      ██\n      ██\n████████",
    "████████\n██      \n██      \n████████\n██    ██\n██    ██\n████████",
    "████████\n      ██\n      ██\n      ██\n      ██\n      ██\n      ██",
    "████████\n██    ██\n██    ██\n████████\n██    ██\n██    ██\n████████",
    "████████\n██    ██\n██    ██\n████████\n      ██\n      ██\n████████",
]
COLON = "    \n████\n████\n    \n████\n████\n    "


def get_time_as_ascii_string(duration: str) -> str:
    pattern = re.compile(r".*(?P<time>\d{2}:\d{2}:\d{2})")
    match = pattern.fullmatch(duration)
    if match is None:
        raise ValueError
    time_str = match.group("time")
    ascii_chars = []
    for time_char in time_str:
        if time_char.isdecimal():
            ascii_chars.append(NUMBERS[int(time_char)])
        else:
            ascii_chars.append(COLON)
    ascii_chars = [char.split("\n") for char in ascii_chars]
    result = ""
    for i in range(0, 7):
        for char in ascii_chars:
            result += char[i] + "    "
        result = result[:-4]
        result += "\n"
    return result


def format_seconds(total_seconds: float) -> str:
    if total_seconds < 0:
        total_seconds *= -1
    years, remainder = divmod(total_seconds, YEARS_IN_SECONDS)
    years = int(years)
    remainder = int(remainder)
    days, remainder = divmod(remainder, DAYS_IN_SECONDS)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    result = ""
    if years != 0:
        if years == 1:
            result += "1 year, "
        else:
            result += f"{years} years, "
    if days != 0:
        if days == 1:
            result += "1 day, "
        else:
            result += f"{days} days, "
    result += f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return result


# "dt" is expected to be a naive datetime
def to_aware_string(dt: datetime | None, tz: ZoneInfo, template: str = "%d/%m/%Y %H:%M:%S") -> str:
    if dt is None:
        return "N/A"
    utc_dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    adjusted_dt = utc_dt.astimezone(tz)
    return adjusted_dt.strftime(template)


def handle_two_digit_year(year: str) -> str:
    if len(year) == 2:
        current_year = datetime.now().year % 100
        if int(year) >= current_year:
            return "20" + year
        else:
            return "19" + year
    elif len(year) == 4:
        return year
    else:
        raise ValueError
