from unittest.mock import patch
from fiscal_bot.handlers import fiscal_bot_tender_handler
import unittest

test_procedures = (
    'fake_procedure_1',
    'fake_procedure_2',
)


@patch("fiscal_bot.handlers.procedures", new=test_procedures)
class TestHandlerCase(unittest.TestCase):

    @patch("fiscal_bot.handlers.process_tender.delay")
    def test_wrong_status(self, process_tender_mock):
        tender = {
            "status": "active.awarded",
            "procurementMethodType": test_procedures[0],
        }
        fiscal_bot_tender_handler(tender)
        process_tender_mock.assert_not_called()

    @patch("fiscal_bot.handlers.process_tender.delay")
    def test_wrong_type(self, process_tender_mock):
        tender = {
            "status": "active.qualification",
            "procurementMethodType": "fake_procedure_0",
        }
        fiscal_bot_tender_handler(tender)
        process_tender_mock.assert_not_called()

    @patch("fiscal_bot.handlers.process_tender.delay")
    def test_success(self, process_tender_mock):
        tender = {
            "id": "134",
            "status": "active.qualification",
            "procurementMethodType": test_procedures[0],
        }
        fiscal_bot_tender_handler(tender)
        process_tender_mock.assert_called_with(tender_id="134")
