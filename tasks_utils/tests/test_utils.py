from unittest.mock import Mock
from tasks_utils.requests import get_request_retry_countdown, get_exponential_request_retry_countdown
from environment_settings import DEFAULT_RETRY_AFTER, EXPONENTIAL_RETRY_MAX
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


class RequestExponentialRetryTestCase(unittest.TestCase):

    def test_wrong_value_type(self):
        task = Mock()
        task.request.retries = 0
        request = Mock()
        countdown = get_exponential_request_retry_countdown(task, request)
        self.assertEqual(countdown, DEFAULT_RETRY_AFTER)

    def test_string(self):
        task = Mock()
        task.request.retries = 0
        request = Mock()
        request.headers = {"Retry-After": "12.5"}
        countdown = get_exponential_request_retry_countdown(task, request)
        self.assertEqual(countdown, 12.5)

    def test_retries_1(self):
        task = Mock()
        task.request.retries = 1
        request = Mock()
        request.headers = {"Retry-After": 10}
        countdown = get_exponential_request_retry_countdown(task, request)
        self.assertEqual(countdown, 10 + 5)

    def test_retries_2(self):
        task = Mock()
        task.request.retries = 2
        request = Mock()
        request.headers = {"Retry-After": 11}
        countdown = get_exponential_request_retry_countdown(task, request)
        self.assertEqual(countdown, 11 + 5 ** 2)

    def test_retries_100(self):
        task = Mock()
        task.request.retries = 100
        request = Mock()
        request.headers = {"Retry-After": 11}
        countdown = get_exponential_request_retry_countdown(task, request)
        self.assertEqual(countdown, EXPONENTIAL_RETRY_MAX)
