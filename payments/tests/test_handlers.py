from unittest.mock import patch
from payments.handlers import payments_tender_handler
from tasks_utils.datetime import get_now
import unittest


class TestHandlerCase(unittest.TestCase):

    @patch("payments.handlers.process_tender")
    def test_process_handler(self, process_tender):
        tender = {
            "id": "qwa",
            "dateModified": get_now().isoformat(),
            "procurementMethodType": "aboveThresholdUA"
        }
        payments_tender_handler(tender)
        process_tender.delay.assert_called_with(tender_id="qwa")


    @patch("payments.handlers.process_tender")
    def test_process_handler_for_non_complaint_procedures(self, process_tender):
        non_complaint_procedures = [
            'belowThreshold',
            'reporting',
            'closeFrameworkAgreementSelectionUA'
        ]
        for pmt in non_complaint_procedures:
            tender = {
                "id": "qwa",
                "dateModified": get_now().isoformat(),
                "procurementMethodType": pmt
            }
            payments_tender_handler(tender)
            self.assertEqual(len(process_tender.delay.mock_calls), 0)
