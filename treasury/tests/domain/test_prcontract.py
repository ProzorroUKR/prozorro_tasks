from app.tests.base import BaseTestCase
from unittest.mock import patch, Mock, call
from copy import deepcopy
from treasury.domain.prcontract import (
    get_first_stage_tender,
    prepare_contract_context,
    prepare_context,
    get_tender_start_date,
    get_award_complaint_period_start_date,
    get_contracts_suppliers_address,
    get_award_qualified_eligible_for_each_bid,
    get_award_qualified_eligible,
    handle_award_qualified_eligible_statuses,
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
        tender_start_date = "2020-09-04T14:57:56.498745+03:00"
        contract = dict(id="222", awardID="22")
        plan = dict(id="1243455")
        tender = dict(
            procurementMethodType="negotiation",
            id="45677",
            contracts=[
                dict(id="111"),
                dict(
                    id="222",
                    suppliers=[
                        dict(
                            address=dict(
                                countryName="Україна",
                                streetAddress="м. Дніпро, вул. Андрія Фабра, 4, 4 поверх",
                                region="Дніпропетровська область",
                            )
                        )
                    ]
                ),
            ],
            awards=[
                dict(id="11"),
                dict(
                    id="22",
                    bid_id="2222",
                    lotID="22222",
                    complaintPeriod=dict(
                        startDate=tender_start_date,
                        endDate="2020-08-13T14:57:57.362745+03:00"
                    ),
                    date=complaint_period_start_date
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
            {
                'id': '2222', 'lotValues': [{'relatedLot': '22222', 'value': 15}],
                'value': 15, 'award_qualified_eligible': None
            },
            {
                'id': '3333', 'lotValues': [{'relatedLot': '22222', 'value': 20}],
                'value': 20, 'award_qualified_eligible': None
            },
        ]
        self.assertEqual(result["tender"]["bids"], expected_bids)
        self.assertEqual(result["tender_bid"], expected_bids[0])
        self.assertEqual(result["secondary_data"]["award_complaint_period_start_date"], complaint_period_start_date)
        self.assertEqual(result["secondary_data"]["tender_start_date"], tender_start_date)
        expected_contracts_suppliers_address = "Україна Дніпропетровська область м. Дніпро, вул. Андрія Фабра, 4, 4 поверх"
        self.assertEqual(
            result["secondary_data"]["contracts_suppliers_address"], expected_contracts_suppliers_address
        )
        self.assertEqual(result["tender_contract"], tender["contracts"][1])
        self.assertEqual(result["cancellation"], tender["cancellations"][0])
        self.assertEqual(result["lot"], tender["lots"][1])

    def test_prepare_context_without_tender_bids(self):
        task = Mock()
        enquiry_period_start_date = "2020-08-13T14:20:07.813257+03:00"
        complaint_period_start_date = "2020-08-13T14:57:56.498745+03:00"
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
                dict(
                    id="222",
                    suppliers=[
                        dict(
                            address=dict(
                                postalCode="49000",
                                countryName="Україна",
                                streetAddress="м. Дніпро, вул. Андрія Фабра, 4, 4 поверх",
                                region="Дніпропетровська область",
                                locality="Дніпро"
                            )
                        )
                    ]
                ),
            ],
            awards=[
                dict(id="11"),
                dict(
                    id="22",
                    lotID="22222",
                    date=complaint_period_start_date
                ),
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
        self.assertEqual(result["secondary_data"]["award_complaint_period_start_date"], complaint_period_start_date)
        self.assertEqual(result["secondary_data"]["tender_start_date"], enquiry_period_start_date)

        expected_contracts_suppliers_address = "49000 Україна Дніпропетровська область Дніпро м. Дніпро, вул. Андрія Фабра, 4, 4 поверх"
        self.assertEqual(
            result["secondary_data"]["contracts_suppliers_address"],  expected_contracts_suppliers_address
        )
        self.assertEqual(result["tender_contract"], tender["contracts"][1])
        self.assertEqual(result["cancellation"], tender["cancellations"][0])
        self.assertEqual(result["lot"], tender["lots"][1])

    def test_get_tender_start_date(self):
        # 1
        start_date = "2020-08-13T14:20:07.813257+03:00"
        tender = {
            "id": 12345,
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

    def test_get_awards_complaint_period_start_date(self):
        # 1
        _award_date = "2020-08-14T12:32:18.080119+03:00"
        tender_award = {
            "date": _award_date,
        }

        result = get_award_complaint_period_start_date(tender_award)
        self.assertEqual(result, _award_date)

    def test_get_contracts_suppliers_address(self):
        tender_contract = {
            "status": "active",
            "suppliers": [
                {
                    "address": {
                        "postalCode": "21100",
                        "countryName": "Україна",
                        "streetAddress": "вул. Данила Галицького, буд. 27, каб. 21",
                        "region": "Вінницька область",
                        "locality": "Вінниця"
                    }
                }
            ]
        }

        result = get_contracts_suppliers_address(tender_contract)
        expected_result = "21100 Україна Вінницька область Вінниця вул. Данила Галицького, буд. 27, каб. 21"
        self.assertEqual(result, expected_result)

        tender_contract = {
            "status": "active",
            "suppliers": [
                {
                    "address": {
                        "region": "Вінницька область",
                        "locality": "Вінниця",
                        "countryName": "Україна",
                        "unknown_field": 123
                    }
                }
            ]
        }
        result = get_contracts_suppliers_address(tender_contract)
        expected_result = "Україна Вінницька область Вінниця"
        self.assertEqual(result, expected_result)

    def test_get_award_qualified_eligible_for_each_bid(self):

        tender = {
            "procurementMethodType": "esco",
            "bids": [
                {
                    "id": 12345
                },
                {
                    "id": 45678
                }
            ]
        }

        expected_result = {
            "procurementMethodType": "esco",
            "bids": [
                {
                    "id": 12345,
                    "award_qualified_eligible": None
                },
                {
                    "id": 45678,
                    "award_qualified_eligible": None
                }
            ]
        }

        result = get_award_qualified_eligible_for_each_bid(tender)
        self.assertEqual(result, expected_result)

    def test_get_award_qualified_eligible(self):
        bid_id = 456789
        bid = {
            "id": bid_id
        }

        # 1
        tender = {
            "procurementMethodType": "aboveThresholdUA",
            "awards": [
                {
                    "status": "active",
                    "bid_id": bid_id,
                }
            ]
        }

        result = get_award_qualified_eligible(tender, bid)
        expected_result = True
        self.assertEqual(result, expected_result)

        tender["awards"][0]["status"] = "cancelled"
        result = get_award_qualified_eligible(tender, bid)
        expected_result = "Рішення скасоване"
        self.assertEqual(result, expected_result)

        tender["awards"][0]["bid_id"] = "there_are_no_award_with_same_id"
        result = get_award_qualified_eligible(tender, bid)
        expected_result = None
        self.assertEqual(result, expected_result)

        # 2
        tender = {
            "procurementMethodType": "aboveThresholdEU",
            "qualifications": [
                {
                    "status": "unsuccessful",
                    "bid_id": 1234,
                },
                {
                    "status": "active",
                    "bid_id": bid_id,
                }
            ]
        }

        result = get_award_qualified_eligible(tender, bid)
        self.assertEqual(result, True)

        tender["qualifications"][1]["bid_id"] = "999999999"
        result = get_award_qualified_eligible(tender, bid)
        self.assertEqual(result, None)

        # 3
        tender = {
            "id": 123456789,
            "procurementMethodType": "closeFrameworkAgreementSelectionUA"
        }

        result = get_award_qualified_eligible(tender, bid)
        self.assertEqual(result, True)

        # 4
        tender = {
            "id": 123456789,
            "procurementMethodType": "priceQuotation"
        }

        result = get_award_qualified_eligible(tender, bid)
        self.assertEqual(result, None)

        # 5
        tender = {
            "id": 123456789,
            "procurementMethodType": "unknown_procurement_method_type"
        }
        result = get_award_qualified_eligible(tender, bid)
        self.assertEqual(result, None)

    def test_handle_award_qualified_eligible_statuses(self):
        # 1
        award = {
            "status": "active"
        }
        result = handle_award_qualified_eligible_statuses(award)
        self.assertEqual(result, True)

        # 2
        award["status"] = "unsuccessful"
        award["title"] = "title1"
        award["description"] = "description1"
        result = handle_award_qualified_eligible_statuses(award)
        self.assertEqual(result, "title1 description1")

        # 3
        award["status"] = "pending"
        result = handle_award_qualified_eligible_statuses(award)
        self.assertEqual(result, None)

        # 4
        award["status"] = "cancelled"
        result = handle_award_qualified_eligible_statuses(award)
        self.assertEqual(result, "Рішення скасоване")

