from treasury.handlers import contract_handler
from unittest.mock import patch
import unittest


class CheckTestCase(unittest.TestCase):

    @patch("treasury.handlers.check_contract")
    def test_contract_handler(self, check_contract_mock):
        contract = {
            "id": "123",
            "status": "active"
        }

        contract_handler(contract)

        check_contract_mock.delay.assert_called_once_with(
            contract_id="123"
        )

    @patch("treasury.handlers.check_contract")
    def test_contract_handler_contract_inactive(self, check_contract_mock):
        contract = {
            "id": "4567",
            "status": "terminated"
        }

        contract_handler(contract)

        check_contract_mock.delay.assert_not_called()
