from unittest.mock import patch
from autoclient_payments.handlers import payments_tender_handler
from tasks_utils.datetime import get_now
import unittest

from tasks_utils.tests.utils import async_test


class TestHandlerCase(unittest.TestCase):
    @async_test
    async def test_process_handler(self):
        tender = {"id": "qwa", "dateModified": get_now().isoformat(), "procurementMethodType": "aboveThresholdUA"}
        with patch("autoclient_payments.handlers.process_tender") as process_tender:
            await payments_tender_handler(tender)
        process_tender.delay.assert_called_with(tender_id="qwa")

    @async_test
    async def test_process_handler_for_non_complaint_procedures(self):
        non_complaint_procedures = ["belowThreshold", "reporting", "closeFrameworkAgreementSelectionUA"]
        for pmt in non_complaint_procedures:
            tender = {"id": "qwa", "dateModified": get_now().isoformat(), "procurementMethodType": pmt}
            with patch("autoclient_payments.handlers.process_tender") as process_tender:
                await payments_tender_handler(tender)
            self.assertEqual(len(process_tender.delay.mock_calls), 0)
