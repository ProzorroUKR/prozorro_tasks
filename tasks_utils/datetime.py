from environment_settings import TIMEZONE
from datetime import datetime, time, timedelta
import dateutil.parser
import json


with open("tasks_utils/holidays.json") as f:
    HOLIDAYS = set(json.load(f).keys())


def is_working_time(dt):
    result = (
        time(9, 0) <= dt.time() <= time(18, 0)
        and dt.weekday() < 5
        and dt.date().isoformat() not in HOLIDAYS
    )
    return result


def get_now():
    return datetime.now(tz=TIMEZONE)


def get_working_datetime(dt):
    """
    Returns the closest business time to what you provided,
    Sun 13:00 -> Mon 9:00
    Friday 18:01 -> Mon 9:00
    etc
    :param dt:
    :return:
    """
    assert dt.tzinfo.zone == TIMEZONE.zone

    # round up microsecond and  seconds
    if dt.microsecond:
        dt = dt.replace(microsecond=0) + timedelta(seconds=1)
    if dt.second:
        dt = dt.replace(second=0) + timedelta(seconds=60)

    # one by one  fix reasons that make this dt "not working(business)"
    if dt.time() < time(9, 0):  # too early
        dt = dt.replace(hour=9, minute=0)

    elif dt.time() > time(18, 0):  # too late
        dt = dt.replace(hour=9, minute=0) + timedelta(days=1)

    while 1:  # if the day increased we have to check it's date again until it's fine
        weekday = dt.weekday()
        if weekday in (5, 6):  # saturday or sunday
            dt = dt.replace(hour=9, minute=0) + timedelta(days=7 - weekday)
            continue

        if dt.date().isoformat() in HOLIDAYS:
            dt = dt.replace(hour=9, minute=0) + timedelta(days=1)
            continue

        break

    return dt


def working_days_count_since(dt, now=None):
    """
    Returns a number of wd since a specified day
    Ex1: dt=Friday 18:00 now=Monday 9:00  result=2 (Friday and Monday)
    Ex2: dt=Friday 18:01 now=Monday 9:00  result=1 (only Monday)
    :param dt: a datetime to start count from
    :param now:
    :return:
    """
    if type(dt) is str:
        dt = dateutil.parser.parse(dt).astimezone(TIMEZONE)
    now = now or get_now()
    assert dt.tzinfo.zone == TIMEZONE.zone
    assert now > dt, "this function goes only forward"

    # get start date (and normalize time)
    if not is_working_time(dt):
        dt = get_working_datetime(dt)
    else:
        dt = dt.replace(hour=9, minute=0, second=0, microsecond=0)
    # count only working days
    count = 0
    while dt <= now:
        if is_working_time(dt):
            count += 1
        dt += timedelta(days=1)

    return count

