from app.tests.base import BaseTestCase
from unittest.mock import patch, Mock, call
from treasury.domain.prcontract import get_first_stage_tender


class TestCase(BaseTestCase):
    @patch("treasury.domain.prcontract.get_public_api_data")
    def test_get_first_stage_tender(self, get_tender_mock):

        first_stage_tender_id = "23456789"
        tender_data_second_stage = dict(
            id="1234",
            procurementMethodType="competitiveDialogueEU.stage2",
            dialogueID=first_stage_tender_id
        )

        tender_data_first_stage = dict(
            id=first_stage_tender_id,
            procurementMethodType="competitiveDialogueEU",
            plans=[dict(id="321")]
        )

        get_tender_mock.return_value = tender_data_first_stage

        result = get_first_stage_tender(tender_data_second_stage, 'some_task')
        expected_result = tender_data_first_stage
        self.assertEqual(result, expected_result)

        first_stage_tender_id = "777779999"
        tender_data_second_stage = dict(
            id="6789",
            procurementMethodType="closeFrameworkAgreementSelectionUA",
            agreements={"tender_id": first_stage_tender_id}
        )
        tender_data_first_stage = dict(
            id=first_stage_tender_id,
            procurementMethodType="closeFrameworkAgreementUA",
            plans=[dict(id="321")]
        )

        get_tender_mock.return_value = tender_data_first_stage

        result = get_first_stage_tender(tender_data_second_stage, 'some_task')
        expected_result = tender_data_first_stage
        self.assertEqual(result, expected_result)

        tender_data_second_stage = dict(
            id="6789",
            procurementMethodType="someMethodType",
        )
        result = get_first_stage_tender(tender_data_second_stage, 'some_task')
        expected_result = tender_data_second_stage
        self.assertEqual(result, expected_result)

        tender_data_second_stage = dict(
            id="7890",
            procurementMethodType="competitiveDialogueEU",
        )
        result = get_first_stage_tender(tender_data_second_stage, 'some_task')
        expected_result = tender_data_second_stage
        self.assertEqual(result, expected_result)
