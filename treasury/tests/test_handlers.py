from datetime import timedelta

from tasks_utils.datetime import get_now
from treasury.handlers import contract_handler
from unittest.mock import patch
import unittest


class CheckTestCase(unittest.TestCase):

    @patch("treasury.handlers.TREASURY_INT_START_DATE", (get_now() - timedelta(days=1)).isoformat())
    @patch("treasury.handlers.check_contract")
    def test_contract_handler(self, check_contract_mock):
        contract = {
            "id": "123",
            "dateModified": get_now().isoformat()
        }

        contract_handler(contract)

        check_contract_mock.delay.assert_called_once_with(
            contract_id="123"
        )

    @patch("treasury.handlers.TREASURY_INT_START_DATE", (get_now() + timedelta(days=1)).isoformat())
    @patch("treasury.handlers.check_contract")
    def test_contract_handler_contract_old(self, check_contract_mock):
        contract = {
            "id": "4567",
            "dateModified": get_now().isoformat()
        }

        contract_handler(contract)

        check_contract_mock.delay.assert_not_called()
