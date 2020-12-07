from unittest.mock import patch
from chronograph.handlers import chronograph_framework_handler
import unittest

from tasks_utils.datetime import get_now


class TestChronographFrameworkHandlerCase(unittest.TestCase):

    @patch("chronograph_framework_handler.handlers.recheck_framework")
    def test_no_next_check(self, recheck_framework):
        framework = {
            "framework_id": "qwerty",
        }
        chronograph_framework_handler(framework)
        recheck_framework.apply_async.assert_not_called()

    @patch("chronograph_framework_handler.handlers.recheck_framework")
    def test_next_check(self, recheck_framework):
        next_check = get_now()
        framework = {
            "framework_id": "qwerty",
            "next_check": next_check.isoformat(),
        }
        cookies = dict(some_cookie="some_test_cookie")
        chronograph_framework_handler(framework)
        recheck_framework.apply_async.assert_called_with(
            kwargs=dict(
                framework_id="qwerty",
                cookies=cookies
            ),
            eta=next_check
        )
