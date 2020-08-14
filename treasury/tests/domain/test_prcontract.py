from app.tests.base import BaseTestCase
from unittest.mock import patch, Mock, call
from copy import deepcopy
from treasury.domain.prcontract import (
    get_first_stage_tender,
    prepare_contract_context,
    prepare_context,
    get_tender_start_date,
)


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
        complaint_period_start_date = "2020-08-13T14:57:56.498745+03:00"
        contract = dict(id="222", awardID="22")
        plan = dict(id="1243455")
        tender = dict(
            procurementMethodType="negotiation",
            id="45677",
            contracts=[
                dict(id="111"),
                dict(id="222"),
            ],
            awards=[
                dict(id="11"),
                dict(
                    id="22",
                    bid_id="2222",
                    lotID="22222",
                    complaintPeriod=dict(
                        startDate=complaint_period_start_date,
                        endDate="2020-08-13T14:57:57.362745+03:00"
                    )
                ),
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
        self.assertEqual(result["tender_start_date"], complaint_period_start_date)
        self.assertEqual(result["tender_award"], tender["awards"][1])
        self.assertEqual(result["tender_contract"], tender["contracts"][1])
        self.assertEqual(result["cancellation"], tender["cancellations"][0])
        self.assertEqual(result["lot"], tender["lots"][1])

    def test_prepare_context_without_tender_bids(self):
        task = Mock()
        enquiry_period_start_date = "2020-08-13T14:20:07.813257+03:00"
        contract = dict(id="222", awardID="22")
        plan = dict(id="1243455")

        tender = dict(
            procurementMethodType="aboveThresholdUA",
            enquiryPeriod=dict(
                startDate=enquiry_period_start_date,
                endDate="2020-08-13T14:20:07.899657+03:00"
            ),
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
        self.assertEqual(result["tender_start_date"], enquiry_period_start_date)
        self.assertEqual(result["tender"]["items"], tender["items"][1:])
        self.assertEqual(result["tender"]["milestones"], tender["milestones"][1:])
        self.assertEqual(result["tender_award"], tender["awards"][1])
        self.assertEqual(result["tender_contract"], tender["contracts"][1])
        self.assertEqual(result["cancellation"], tender["cancellations"][0])
        self.assertEqual(result["lot"], tender["lots"][1])

    def test_get_tender_start_date(self):
        # 1
        start_date = "2020-08-13T14:20:07.813257+03:00"
        tender = {
            "procurementMethodType": "aboveThresholdUA",
            "enquiryPeriod": {
                "startDate": start_date,
                "endDate": "2020-08-13T14:20:07.899657+03:00"
            }
        }

        result = get_tender_start_date(tender, {}, {})
        self.assertEqual(result, start_date)

        # 2
        tender["procurementMethodType"] = "negotiation.quick"
        complaint_period_start_date = "2020-08-13T14:57:56.498745+03:00"
        tender_award = {
            "complaintPeriod": {
                "startDate": complaint_period_start_date,
                "endDate": "2020-08-13T14:57:57.362745+03:00"
            },
        }
        result = get_tender_start_date(tender, tender_award, {})
        self.assertEqual(result, complaint_period_start_date)

        # 3
        tender["procurementMethodType"] = "reporting"
        contract_date_signed = "2020-05-22T03:06:08.072653+03:00"
        tender_contract = {
            "status": "active",
            "dateSigned": contract_date_signed,
        }
        result = get_tender_start_date(tender, {}, tender_contract)
        self.assertEqual(result, contract_date_signed)

        # 4
        tender["procurementMethodType"] = "priceQuotation"
        tender_period_start_date = "2020-05-22T03:06:08.072653+03:00"

        tender["tenderPeriod"] = {
            "startDate": tender_period_start_date,
            "endDate": "2021-07-15T12:29:00+03:00"
        }
        result = get_tender_start_date(tender, {}, {})
        self.assertEqual(result, tender_period_start_date)

        # 5
        tender["procurementMethodType"] = "unknown"
        result = get_tender_start_date(tender, {}, {})
        self.assertEqual(result, None)
