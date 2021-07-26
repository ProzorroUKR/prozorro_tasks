from datetime import timedelta

from tasks_utils.datetime import get_now
from tasks_utils.tests.utils import async_test
from treasury.handlers import contract_handler
from unittest.mock import patch
import unittest


class CheckTestCase(unittest.TestCase):

    @async_test
    async def test_contract_handler(self):
        contract = {
            "id": "123",
            "dateModified": get_now().isoformat()
        }

        with patch("treasury.handlers.TREASURY_INT_START_DATE", (get_now() - timedelta(days=1)).isoformat()), \
             patch("treasury.handlers.check_contract") as check_contract_mock:
                await contract_handler(contract)

        check_contract_mock.delay.assert_called_once_with(
            contract_id="123"
        )

    @async_test
    async def test_contract_handler_contract_old(self):
        contract = {
            "id": "4567",
            "dateModified": get_now().isoformat()
        }

        with patch("treasury.handlers.TREASURY_INT_START_DATE", (get_now() + timedelta(days=1)).isoformat()), \
             patch("treasury.handlers.check_contract") as check_contract_mock:
                await contract_handler(contract)

        check_contract_mock.delay.assert_not_called()
