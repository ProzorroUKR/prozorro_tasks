from unittest.mock import patch
from edr_bot.handlers import edr_bot_tender_handler
import unittest

test_pre_qualification_procedures = (
    'fake_qualification_pro',
)
test_qualification_procedures = (
    'fake_pre_qualification_pro',
)
test_qualification_procedures_limited = (
    'fake_qualification_pro_limited',
)


@patch("edr_bot.handlers.pre_qualification_procedures", new=test_pre_qualification_procedures)
@patch("edr_bot.handlers.qualification_procedures", new=test_qualification_procedures)
@patch("edr_bot.handlers.qualification_procedures_limited", new=test_qualification_procedures_limited)
class TestHandlerCase(unittest.TestCase):

    @patch("edr_bot.handlers.process_tender")
    def test_just_active_pre_qualification(self, process_tender):
        tender = {
            "status": "active",
            "procurementMethodType": test_pre_qualification_procedures[0],
        }
        edr_bot_tender_handler(tender)
        process_tender.delay.assert_not_called()

    @patch("edr_bot.handlers.process_tender")
    def test_just_active_qualification(self, process_tender):
        tender = {
            "status": "active",
            "procurementMethodType": test_qualification_procedures[0],
        }
        edr_bot_tender_handler(tender)
        process_tender.delay.assert_not_called()

    @patch("edr_bot.handlers.process_tender")
    def test_just_draft_qualification_limited(self, process_tender):
        tender = {
            "status": "draft",
            "procurementMethodType": test_qualification_procedures_limited[0],
        }
        edr_bot_tender_handler(tender)
        process_tender.delay.assert_not_called()

    @patch("edr_bot.handlers.process_tender")
    def test_active_qualification_wrong_type(self, process_tender):
        tender = {
            "status": "active.qualification",
            "procurementMethodType": test_pre_qualification_procedures[0],
        }
        edr_bot_tender_handler(tender)
        process_tender.delay.assert_not_called()

    @patch("edr_bot.handlers.process_tender")
    def test_active_qualification_limited_wrong_type(self, process_tender):
        tender = {
            "status": "active",
            "procurementMethodType": test_qualification_procedures[0],
        }
        edr_bot_tender_handler(tender)
        process_tender.delay.assert_not_called()

    @patch("edr_bot.handlers.process_tender")
    def test_active_pre_qualification_wrong_type(self, process_tender):
        tender = {
            "status": "active.pre-qualification",
            "procurementMethodType": test_qualification_procedures[0],
        }
        edr_bot_tender_handler(tender)
        process_tender.delay.assert_not_called()

    @patch("edr_bot.handlers.process_tender")
    def test_active_pre_qualification(self, process_tender):
        tender = {
            "id": "qwerty",
            "status": "active.pre-qualification",
            "procurementMethodType": test_pre_qualification_procedures[0],
        }
        edr_bot_tender_handler(tender)
        process_tender.delay.assert_called_with(tender_id="qwerty")

    @patch("edr_bot.handlers.process_tender")
    def test_active_qualification(self, process_tender):
        tender = {
            "id": "qwa",
            "status": "active.qualification",
            "procurementMethodType": test_qualification_procedures[0],
        }
        edr_bot_tender_handler(tender)
        process_tender.delay.assert_called_with(tender_id="qwa")

    @patch("edr_bot.handlers.process_tender")
    def test_active_qualification_limited(self, process_tender):
        tender = {
            "id": "qwe",
            "status": "active",
            "procurementMethodType": test_qualification_procedures_limited[0],
        }
        edr_bot_tender_handler(tender)
        process_tender.delay.assert_called_with(tender_id="qwe")
