from unittest.mock import patch
from chronograph.handlers import chronograph_handler
import unittest

from tasks_utils.datetime import get_now


class TestChronographFrameworkHandlerCase(unittest.TestCase):

    @patch("chronograph.handlers.recheck")
    def test_no_next_check(self, recheck):
        framework = {
            "id": "qwerty",
        }
        handler = chronograph_handler("framework")
        handler(framework)
        recheck.apply_async.assert_not_called()

    @patch("chronograph.handlers.recheck")
    def test_next_check(self, recheck):
        next_check = get_now()
        framework = {
            "id": "qwerty",
            "next_check": next_check.isoformat(),
        }
        handler = chronograph_handler("framework")
        handler(framework)
        recheck.apply_async.assert_called_with(
            kwargs=dict(
                obj_name="framework",
                obj_id="qwerty",
            ),
            eta=next_check
        )
