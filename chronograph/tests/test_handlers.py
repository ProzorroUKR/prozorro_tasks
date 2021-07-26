from unittest.mock import patch
from chronograph.handlers import chronograph_handler
import unittest

from tasks_utils.datetime import get_now
from tasks_utils.tests.utils import async_test


class TestChronographFrameworkHandlerCase(unittest.TestCase):

    @async_test
    async def test_no_next_check(self):
        framework = {
            "id": "qwerty",
        }
        handler = chronograph_handler("framework")
        with patch("chronograph.handlers.recheck") as recheck:
            await handler(framework)
        recheck.apply_async.assert_not_called()

    @async_test
    async def test_next_check(self):
        next_check = get_now()
        framework = {
            "id": "qwerty",
            "next_check": next_check.isoformat(),
        }
        handler = chronograph_handler("framework")
        with patch("chronograph.handlers.recheck") as recheck:
            await handler(framework)
        recheck.apply_async.assert_called_with(
            kwargs=dict(
                obj_name="framework",
                obj_id="qwerty",
            ),
            eta=next_check
        )
