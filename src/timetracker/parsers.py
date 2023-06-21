import re
from calendar import monthrange
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo


# "dt" is expected to be a naive datetime
def to_aware_string(dt: datetime, tz: ZoneInfo) -> str:
    utc_dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    adjusted_dt = utc_dt.astimezone(tz)
    return adjusted_dt.strftime("%d/%m/%Y %H:%M:%S")


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


def parse_date(dt: str) -> datetime:
    pattern = re.compile(r"(?P<day>\d{1,2})\/(?P<month>\d{1,2})\/(?P<year>(?:\d{2}){1,2})")
    if match := pattern.fullmatch(dt):
        day, month, year = match.group("day", "month", "year")
        year = handle_two_digit_year(year)
        try:
            date = datetime(int(year), int(month), int(day))
        except ValueError:
            print(f"{dt} is not a valid format for a date")
        return date
    elif dt.lower() == "today":
        return datetime.now()
    elif dt.lower() == "yesterday":
        return datetime.now() - timedelta(days=1)
    raise ValueError


def parse_date_range(start_input: str, end_input: Optional[str]) -> tuple[datetime, datetime]:
    if end_input == "week":
        today = datetime.now()

        if start_input == "this":
            start_dt = today - timedelta(days=today.weekday())
            end_dt = today + timedelta(days=6-today.weekday())
        elif start_input == "last":
            start_dt = today - timedelta(weeks=1, days=today.weekday())
            end_dt = today - timedelta(days=1+today.weekday())
        else:
            raise ValueError
    elif end_input == "month":
        year = datetime.now().year

        if start_input == "this":
            month = datetime.now().month
        elif start_input == "last":
            month = datetime.now().month
            if month == 1:
                month = 12
                year -= 1
            else:
                month -= 1
        else:
            raise ValueError

        start_dt = datetime(year, month, 1)
        day = monthrange(year, month)
        end_dt = datetime(year, month, day)
    elif end_input == "year":
        if start_input == "this":
            year = datetime.now().year
        elif start_input == "last":
            year = datetime.now().year - 1
        else:
            raise ValueError

        start_dt = datetime(year, 1, 1)
        end_dt = datetime(year, 12, 31)
    elif end_input is None:
        start_dt = parse_date(start_input)
        end_dt = parse_date(start_input)
    else:
        start_dt = parse_date(start_input)
        end_dt = parse_date(end_input)

    start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
    return (start_dt, end_dt)
