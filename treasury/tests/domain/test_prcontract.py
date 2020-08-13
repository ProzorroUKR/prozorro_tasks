from app.tests.base import BaseTestCase
from unittest.mock import patch, Mock, call
from treasury.domain.prcontract import get_first_stage_tender
from treasury.domain.prcontract import prepare_contract_context, prepare_context
from copy import deepcopy


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

        result = get_first_stage_tender('some_task', tender_data_second_stage)
        expected_result = tender_data_first_stage
        self.assertEqual(result, expected_result)

        first_stage_tender_id = "777779999"
        tender_data_second_stage = dict(
            id="6789",
            procurementMethodType="closeFrameworkAgreementSelectionUA",
            agreements=
            [
                {
                    "agreementID": "UA-2020-05-18-000029-a-a1",
                    "status": "active",
                    "tender_id": first_stage_tender_id
                }
            ]
        )
        tender_data_first_stage = dict(
            id=first_stage_tender_id,
            procurementMethodType="closeFrameworkAgreementUA",
            plans=[dict(id="321")]
        )

        get_tender_mock.return_value = tender_data_first_stage

        result = get_first_stage_tender('some_task', tender_data_second_stage)
        expected_result = tender_data_first_stage
        self.assertEqual(result, expected_result)

        tender_data_second_stage = dict(
            id="6789",
            procurementMethodType="someMethodType",
        )
        result = get_first_stage_tender('some_task', tender_data_second_stage)
        expected_result = tender_data_second_stage
        self.assertEqual(result, expected_result)

        tender_data_second_stage = dict(
            id="7890",
            procurementMethodType="competitiveDialogueEU",
        )
        result = get_first_stage_tender('some_task', tender_data_second_stage)
        expected_result = tender_data_second_stage
        self.assertEqual(result, expected_result)

    def test_contract_context(self):
        contract = dict(
            documents=[
                dict(
                    id="11",
                    documentOf="change",
                    relatedItem="1",
                ),
                dict(
                    id="22",
                    documentOf="item",
                    relatedItem="1",
                ),
            ],
            changes=[
                dict(id="1"),
                dict(id="2"),
            ]
        )
        prepare_contract_context(contract)
        self.assertEqual({d["id"] for d in contract["documents"]}, set())  # {"22"})  We disable docs temporary
        # self.assertEqual({d["id"] for d in contract["changes"][0]["documents"]}, {"11"})
        self.assertNotIn("documents", contract["changes"][0])
        self.assertNotIn("documents", contract["changes"][1])

    def test_prepare_context(self):
        task = Mock()
        contract = dict(id="222", awardID="22")
        plan = dict(id="1243455")
        tender = dict(
            id="45677",
            contracts=[
                dict(id="111"),
                dict(id="222"),
            ],
            awards=[
                dict(id="11"),
                dict(id="22", bid_id="2222", lotID="22222"),
            ],
            bids=[
                dict(id="1111", lotValues=[dict(relatedLot="11111", value=12)]),
                dict(id="2222", lotValues=[dict(relatedLot="22222", value=15)]),
                dict(id="3333", lotValues=[dict(relatedLot="22222", value=20)]),
                dict(id="4444", status="deleted"),
            ],
            lots=[
                dict(id="11111"),
                dict(id="22222"),
            ],
            cancellations=[
                dict(relatedLot="22222", status="active"),
            ],
            milestones=[
                dict(relatedLot="11111"),
                dict(relatedLot="22222"),
            ],
            items=[
                dict(relatedLot="11111"),
                dict(relatedLot="22222"),
            ],
            documents=[
                dict(
                    title="audit_45677_22222.yaml",
                    url="<audit_url>",
                )
            ]
        )
        audit_content = b"""timeline:
          auction_start:
            initial_bids:
            - amount: 77400.0
              bidder: 1111
              date: '2019-02-08T12:48:23.869715+02:00'
            - amount: 85000.0
              bidder: 2222
              date: '2019-02-08T12:45:04.619610+02:00'"""

        with patch("treasury.domain.prcontract.prepare_contract_context") as prepare_contract_mock:
            with patch("treasury.domain.prcontract.download_file") as download_file_mock:
                download_file_mock.return_value = None, audit_content
                result = prepare_context(task, contract, deepcopy(tender), plan)

        prepare_contract_mock.assert_called_once_with(contract)
        self.assertIs(result["contract"], contract)
        self.assertEqual(result["initial_bids"], {"1111": 77400.0, "2222": 85000.0})
        self.assertEqual(result["tender"]["items"], tender["items"][1:])
        self.assertEqual(result["tender"]["milestones"], tender["milestones"][1:])
        expected_bids = [
            {'id': '2222', 'lotValues': [{'relatedLot': '22222', 'value': 15}], 'value': 15},
            {'id': '3333', 'lotValues': [{'relatedLot': '22222', 'value': 20}], 'value': 20},
        ]
        self.assertEqual(result["tender"]["bids"], expected_bids)
        self.assertEqual(result["tender_bid"], expected_bids[0])
        self.assertEqual(result["tender_award"], tender["awards"][1])
        self.assertEqual(result["tender_contract"], tender["contracts"][1])
        self.assertEqual(result["cancellation"], tender["cancellations"][0])
        self.assertEqual(result["lot"], tender["lots"][1])

    def test_prepare_context_without_tender_bids(self):
        task = Mock()
        contract = dict(id="222", awardID="22")
        plan = dict(id="1243455")
        tender = dict(
            id="45677",
            contracts=[
                dict(id="111"),
                dict(id="222"),
            ],
            awards=[
                dict(id="11"),
                dict(id="22", lotID="22222"),
            ],
            lots=[
                dict(id="11111"),
                dict(id="22222"),
            ],
            cancellations=[
                dict(relatedLot="22222", status="active"),
            ],
            milestones=[
                dict(relatedLot="11111"),
                dict(relatedLot="22222"),
            ],
            items=[
                dict(relatedLot="11111"),
                dict(relatedLot="22222"),
            ],
            documents=[]
        )

        with patch("treasury.domain.prcontract.prepare_contract_context") as prepare_contract_mock:
            result = prepare_context(task, contract, deepcopy(tender), plan)

        prepare_contract_mock.assert_called_once_with(contract)
        self.assertIs(result["contract"], contract)
        self.assertEqual(result["tender_bid"], {})
        self.assertEqual(result["tender"]["bids"], [])
        self.assertEqual(result["initial_bids"], {})
        self.assertEqual(result["tender"]["items"], tender["items"][1:])
        self.assertEqual(result["tender"]["milestones"], tender["milestones"][1:])
        self.assertEqual(result["tender_award"], tender["awards"][1])
        self.assertEqual(result["tender_contract"], tender["contracts"][1])
        self.assertEqual(result["cancellation"], tender["cancellations"][0])
        self.assertEqual(result["lot"], tender["lots"][1])
