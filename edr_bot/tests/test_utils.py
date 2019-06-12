from unittest.mock import Mock
from edr_bot.utils import get_request_retry_countdown
from edr_bot.settings import DEFAULT_RETRY_AFTER
import unittest


class RequestRetryTestCase(unittest.TestCase):

    def test_wrong_value_type(self):
        request = Mock()
        countdown = get_request_retry_countdown(request)
        self.assertEqual(countdown, DEFAULT_RETRY_AFTER)

    def test_no_value(self):
        request = Mock()
        request.headers = {}
        countdown = get_request_retry_countdown(request)
        self.assertEqual(countdown, DEFAULT_RETRY_AFTER)

    def test_wrong_value(self):
        request = Mock()
        request.headers = {"Retry-After": "sundown"}
        countdown = get_request_retry_countdown(request)
        self.assertEqual(countdown, DEFAULT_RETRY_AFTER)

    def test_string(self):
        request = Mock()
        request.headers = {"Retry-After": "12.5"}
        countdown = get_request_retry_countdown(request)
        self.assertEqual(countdown, 12.5)

    def test_float(self):
        request = Mock()
        request.headers = {"Retry-After": 130.1}
        countdown = get_request_retry_countdown(request)
        self.assertEqual(countdown, 130.1)
