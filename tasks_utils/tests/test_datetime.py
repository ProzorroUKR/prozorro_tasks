from unittest.mock import patch
from environment_settings import TIMEZONE
from tasks_utils.datetime import get_working_datetime, working_days_count_since
from datetime import datetime, timedelta
import unittest

HOLIDAYS = {
    "2019-03-08",
    "2019-05-01",
}


@patch("tasks_utils.datetime.HOLIDAYS", new=HOLIDAYS)
class GetWorkingTimeCase(unittest.TestCase):

    def test_working_time(self):
        now = TIMEZONE.localize(datetime(2019, 3, 19, 14, 30, 45, 12))

        result = get_working_datetime(now)

        self.assertEqual(
            result,
            TIMEZONE.localize(datetime(2019, 3, 19, 14, 31))
        )

    def test_morning(self):
        now = TIMEZONE.localize(datetime(2019, 3, 19, 6, 30, 1, 1))

        result = get_working_datetime(now)

        self.assertEqual(
            result,
            TIMEZONE.localize(datetime(2019, 3, 19, 9))
        )

    def test_evening(self):
        now = TIMEZONE.localize(datetime(2019, 3, 19, 18, 0, 0, 1))

        result = get_working_datetime(now)

        self.assertEqual(
            result,
            TIMEZONE.localize(datetime(2019, 3, 20, 9))
        )

    def test_saturday(self):
        now = TIMEZONE.localize(datetime(2019, 3, 23, 9, 30))

        result = get_working_datetime(now)

        self.assertEqual(
            result,
            TIMEZONE.localize(datetime(2019, 3, 25, 9))
        )

    def test_sunday(self):
        now = TIMEZONE.localize(datetime(2019, 3, 24, 6, 30))

        result = get_working_datetime(now)

        self.assertEqual(
            result,
            TIMEZONE.localize(datetime(2019, 3, 25, 9))
        )

    def test_holiday(self):
        now = TIMEZONE.localize(datetime(2019, 3, 8, 12, 30))

        result = get_working_datetime(now)

        self.assertEqual(
            result,
            TIMEZONE.localize(datetime(2019, 3, 11, 9))
        )


@patch("tasks_utils.datetime.HOLIDAYS", new=HOLIDAYS)
class WorkingDaysCountSinceCase(unittest.TestCase):

    def test_same_working_day(self):
        dt = TIMEZONE.localize(datetime(2019, 3, 19, 14, 30, 45, 12))
        now = dt + timedelta(seconds=10)
        result = working_days_count_since(dt, now=now)
        self.assertEqual(result, 1)

    def test_next_working_day(self):
        dt = TIMEZONE.localize(datetime(2019, 3, 19, 14, 30, 45, 12))
        now = dt + timedelta(days=1, hours=2)
        result = working_days_count_since(dt, now=now)
        self.assertEqual(result, 2)

    def test_non_working_time(self):
        dt = TIMEZONE.localize(datetime(2019, 3, 19, 7, 30))
        now = dt + timedelta(hours=3)
        result = working_days_count_since(dt, now=now)
        self.assertEqual(result, 1)

    def test_with_string(self):
        now = TIMEZONE.localize(datetime(2019, 3, 19, 7, 30))
        result = working_days_count_since("2019-03-18T11:59:34.750959+02:00", now=now)
        self.assertEqual(result, 1)

    # friday - monday cases
    def test_friday_evening_to_monday_morning(self):
        dt = TIMEZONE.localize(datetime(2019, 3, 22, 18, 1))
        now = TIMEZONE.localize(datetime(2019, 3, 25, 8, 59))
        result = working_days_count_since(dt, now=now)
        self.assertEqual(result, 0)

    def test_friday_to_monday(self):
        dt = TIMEZONE.localize(datetime(2019, 3, 22, 18))
        now = TIMEZONE.localize(datetime(2019, 3, 25, 9))
        result = working_days_count_since(dt, now=now)
        self.assertEqual(result, 2)

    def test_friday_to_monday_morning(self):
        dt = TIMEZONE.localize(datetime(2019, 3, 22, 18))
        now = TIMEZONE.localize(datetime(2019, 3, 25, 8, 59))
        result = working_days_count_since(dt, now=now)
        self.assertEqual(result, 1)

    def test_evening_friday_to_monday(self):
        dt = TIMEZONE.localize(datetime(2019, 3, 22, 18, 1))
        now = TIMEZONE.localize(datetime(2019, 3, 25, 9))
        result = working_days_count_since(dt, now=now)
        self.assertEqual(result, 1)

    # weekends
    def test_saturday_sunday(self):
        dt = TIMEZONE.localize(datetime(2019, 3, 23, 9, 1))
        now = TIMEZONE.localize(datetime(2019, 3, 24, 18))
        result = working_days_count_since(dt, now=now)
        self.assertEqual(result, 0)

    # holidays
    def test_on_holiday(self):
        dt = TIMEZONE.localize(datetime(2019, 3, 8, 9, 1))
        now = TIMEZONE.localize(datetime(2019, 3, 8, 18))
        result = working_days_count_since(dt, now=now)
        self.assertEqual(result, 0)

    def test_from_holiday_to_sunday(self):
        dt = TIMEZONE.localize(datetime(2019, 3, 8, 9, 1))
        now = TIMEZONE.localize(datetime(2019, 3, 10, 18))
        result = working_days_count_since(dt, now=now)
        self.assertEqual(result, 0)

    def test_from_holiday_to_monday(self):
        dt = TIMEZONE.localize(datetime(2019, 3, 8, 9, 1))
        now = TIMEZONE.localize(datetime(2019, 3, 11, 18))
        result = working_days_count_since(dt, now=now)
        self.assertEqual(result, 1)

    def test_from_holiday_evening_to_monday(self):
        dt = TIMEZONE.localize(datetime(2019, 3, 8, 23, 59))
        now = TIMEZONE.localize(datetime(2019, 3, 11, 18))
        result = working_days_count_since(dt, now=now)
        self.assertEqual(result, 1)

    def test_from_holiday_to_monday_evening(self):
        dt = TIMEZONE.localize(datetime(2019, 3, 8, 9, 1))
        now = TIMEZONE.localize(datetime(2019, 3, 11, 23, 59))
        result = working_days_count_since(dt, now=now)
        self.assertEqual(result, 1)

    # weeks
    def test_week(self):
        dt = TIMEZONE.localize(datetime(2019, 3, 11, 6))
        now = TIMEZONE.localize(datetime(2019, 3, 17, 23, 59))
        result = working_days_count_since(dt, now=now)
        self.assertEqual(result, 5)

    def test_week_with_a_holiday(self):
        dt = TIMEZONE.localize(datetime(2019, 3, 4, 6))
        now = TIMEZONE.localize(datetime(2019, 3, 10, 23, 59))
        result = working_days_count_since(dt, now=now)
        self.assertEqual(result, 4)

    def test_week_with_a_holiday_and_weekends(self):
        dt = TIMEZONE.localize(datetime(2019, 3, 1, 18, 1))
        now = TIMEZONE.localize(datetime(2019, 3, 11, 8, 59))
        result = working_days_count_since(dt, now=now)
        self.assertEqual(result, 4)
