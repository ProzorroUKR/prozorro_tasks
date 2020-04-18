from unittest.mock import patch
from payments.handlers import payments_tender_handler
import unittest


class TestHandlerCase(unittest.TestCase):

    @patch("payments.handlers.process_tender")
    def test_process_handler(self, process_tender):
        tender = {"id": "qwa"}
        payments_tender_handler(tender)
        process_tender.delay.assert_called_with(tender_id="qwa")
