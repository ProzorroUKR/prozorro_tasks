from environment_settings import TIMEZONE
from datetime import datetime, time, timedelta
import dateutil.parser
import json

# from https://github.com/ProzorroUKR/standards/tree/master/calendar
with open("tasks_utils/workdays_off.json") as f:
    HOLIDAYS = set(json.load(f))

with open("tasks_utils/weekends_on.json") as f:
    WORKING_WEEKENDS = set(json.load(f))


def is_working_time(dt, custom_wd=None, working_weekends_enabled=False):
    if custom_wd:
        start, end = time(*custom_wd["start"]), time(*custom_wd["end"])
    else:
        start, end = time(9, 0), time(21, 0)

    result = (
        start <= dt.time() <= end
        and (dt.weekday() < 5 or working_weekends_enabled and dt.date().isoformat() in WORKING_WEEKENDS)
        and dt.date().isoformat() not in HOLIDAYS
    )
    return result


def get_now():
    return datetime.now(tz=TIMEZONE)


def get_working_datetime(dt, custom_wd=None, working_weekends_enabled=False):
    """
    Returns the closest business time to what you provided,
    Sun 13:00 -> Mon 9:00
    Friday 21:01 -> Mon 9:00
    etc
    :param dt:
    :param custom_wd:
    :param working_weekends_enabled:
    :return:
    """
    assert dt.tzinfo.zone == TIMEZONE.zone

    start_hour, start_minute = 9, 0
    end_hour, end_minute = 21, 0
    if custom_wd:
        start_hour, start_minute = custom_wd['start']
        end_hour, end_minute = custom_wd['end']

    # round up microsecond and  seconds
    if dt.microsecond:
        dt = dt.replace(microsecond=0) + timedelta(seconds=1)
    if dt.second:
        dt = dt.replace(second=0) + timedelta(seconds=60)

    # one by one  fix time reasons that make this dt "not working(business)"
    if dt.time() < time(start_hour, start_minute):  # too early
        dt = dt.replace(hour=start_hour, minute=start_minute)

    elif dt.time() > time(end_hour, end_minute):  # too late
        dt = dt.replace(hour=start_hour, minute=start_minute) + timedelta(days=1)

    while 1:  # increment days and check until it's fine
        weekday = dt.weekday()
        if weekday in (5, 6) and (  # saturday or sunday
           not working_weekends_enabled or dt.date().isoformat() not in WORKING_WEEKENDS):
            dt = dt.replace(hour=start_hour, minute=start_minute) + timedelta(days=7 - weekday)
            continue

        if dt.date().isoformat() in HOLIDAYS:
            dt = dt.replace(hour=start_hour, minute=start_minute) + timedelta(days=1)
            continue

        break

    return dt


def working_days_count_since(dt, now=None, custom_wd=None, working_weekends_enabled=False):
    """
    Returns a number of wd since a specified day
    Ex1: dt=Friday 18:00 now=Monday 9:00  result=2 (Friday and Monday)
    Ex2: dt=Friday 18:01 now=Monday 9:00  result=1 (only Monday)
    :param dt: a datetime to start count from
    :param now:
    :param custom_wd:
    :param working_weekends_enabled:
    :return:
    """
    if type(dt) is str:
        dt = dateutil.parser.parse(dt).astimezone(TIMEZONE)
    now = now or get_now()
    assert dt.tzinfo.zone == TIMEZONE.zone
    assert now > dt, "this function goes only forward"

    # get start date (and normalize time)
    if not is_working_time(dt, custom_wd=custom_wd, working_weekends_enabled=working_weekends_enabled):
        dt = get_working_datetime(dt, custom_wd=custom_wd, working_weekends_enabled=working_weekends_enabled)
    else:
        hour, minute = 9, 0
        if custom_wd:
            hour, minute = custom_wd['start']
        dt = dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
    # count only working days
    count = 0
    while dt <= now:
        if is_working_time(dt, custom_wd=custom_wd, working_weekends_enabled=working_weekends_enabled):
            count += 1
        dt += timedelta(days=1)

    return count

