from treasury.handlers import contract_handler
from unittest.mock import patch
import unittest


class CheckTestCase(unittest.TestCase):

    @patch("treasury.handlers.check_contract")
    def test_get_org_catalog(self, check_contract_mock):
        contract_id = "123"

        contract_handler(dict(id=contract_id))

        check_contract_mock.delay.assert_called_once_with(
            contract_id=contract_id
        )

