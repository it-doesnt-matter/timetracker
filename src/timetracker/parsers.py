import re
import sys
from calendar import monthrange
from datetime import datetime, timedelta
from typing import Optional

from .error_utils import print_error_box
from .time_utils import handle_two_digit_year


def parse_date(dt: str) -> datetime:
    pattern = re.compile(r"(?P<day>\d{1,2})\/(?P<month>\d{1,2})\/(?P<year>(?:\d{2}){1,2})")
    if match := pattern.fullmatch(dt):
        day, month, year = match.group("day", "month", "year")
        year = handle_two_digit_year(year)
        try:
            date = datetime(int(year), int(month), int(day))
        except ValueError as e:
            print_error_box(e, "Invalid date")
            sys.exit(1)
        return date
    elif dt.lower() == "today":
        return datetime.now()
    elif dt.lower() == "yesterday":
        return datetime.now() - timedelta(days=1)
    print_error_box(
        (
            "a date must have the following format: dd/mm/yyyy\n"
            'alternatively the keywords "today" and "yesterday" are also allowed'
        ),
        "Invalid date!"
    )
    sys.exit(1)


def parse_date_range(start_input: str, end_input: Optional[str]) -> tuple[datetime, datetime]:
    if end_input == "week":
        today = datetime.now()

        if start_input == "this":
            start_dt = today - timedelta(days=today.weekday())
            end_dt = today + timedelta(days=6 - today.weekday())
        elif start_input == "last":
            start_dt = today - timedelta(weeks=1, days=today.weekday())
            end_dt = today - timedelta(days=1 + today.weekday())
        else:
            print_error_box(
                'did you perhaps mean "this week" or "last week"?', "Invalid date range!"
            )
            sys.exit(1)
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
            print_error_box(
                'did you perhaps mean "this month" or "last month"?', "Invalid date range!"
            )
            sys.exit(1)

        start_dt = datetime(year, month, 1)
        _, day = monthrange(year, month)
        end_dt = datetime(year, month, day)
    elif end_input == "year":
        if start_input == "this":
            year = datetime.now().year
        elif start_input == "last":
            year = datetime.now().year - 1
        else:
            print_error_box(
                'did you perhaps mean "this year" or "last year"?', "Invalid date range!"
            )
            sys.exit(1)

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
