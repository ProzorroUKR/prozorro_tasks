from unittest.mock import patch
from fiscal_bot.handlers import fiscal_bot_tender_handler
import unittest

from tasks_utils.tests.utils import async_test

test_procedures = (
    'fake_procedure_1',
    'fake_procedure_2',
)


@patch("fiscal_bot.handlers.fiscal_procedures", new=test_procedures)
class TestHandlerCase(unittest.TestCase):

    @async_test
    async def test_wrong_status(self):
        tender = {
            "status": "active.auction",
            "procurementMethodType": test_procedures[0],
        }
        with patch("fiscal_bot.handlers.process_tender.delay") as process_tender_mock:
            await fiscal_bot_tender_handler(tender)
        process_tender_mock.assert_not_called()

    @async_test
    async def test_wrong_type(self):
        tender = {
            "status": "active.awarded",
            "procurementMethodType": "fake_procedure_0",
        }
        with patch("fiscal_bot.handlers.process_tender.delay") as process_tender_mock:
            await fiscal_bot_tender_handler(tender)
        process_tender_mock.assert_not_called()

    @async_test
    async def test_success_qualifications(self):
        tender = {
            "id": "134",
            "status": "active.qualification",
            "procurementMethodType": test_procedures[0],
        }
        with patch("fiscal_bot.handlers.process_tender.delay") as process_tender_mock:
            await fiscal_bot_tender_handler(tender)
        process_tender_mock.assert_called_with(tender_id="134")

    @async_test
    async def test_success(self):
        tender = {
            "id": "134",
            "status": "active.awarded",
            "procurementMethodType": test_procedures[0],
        }

        with patch("fiscal_bot.handlers.process_tender.delay") as process_tender_mock:
            await fiscal_bot_tender_handler(tender)
        process_tender_mock.assert_called_with(tender_id="134")
