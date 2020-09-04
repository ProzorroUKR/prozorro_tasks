from app.tests.base import BaseTestCase
from unittest.mock import patch, Mock, call
from copy import deepcopy
from treasury.domain.prcontract import (
    get_first_stage_tender,
    prepare_contract_context,
    prepare_context,
    get_tender_start_date,
    get_award_complaint_period_start_date,
    get_custom_address_string,
    get_award_qualified_eligible_for_each_bid,
    get_award_qualified_eligible,
    handle_award_qualified_eligible_statuses,
    get_name_from_organization,
    get_bid_subcontracting_details,
    get_procuring_entity_kind,
    get_contract_date,
)


class TestCase(BaseTestCase):

    def test_get_contract_date(self):
        # 1
        contract = {
            "dateSigned": "2020-06-15T10:34:42.821494+03:00"
        }
        result = get_contract_date(contract, tender={})
        self.assertEqual(result, "2020-06-15T10:34:42.821494+03:00")

        # 2
        contract = {
            "id": "900000000"
        }
        tender = {
            "contracts": [
                {
                    "id": "900000000",
                    "date": "2020-01-01T10:37:44.884962+03:00"
                }
            ]
        }
        result = get_contract_date(contract, tender)
        self.assertEqual(result, "2020-01-01T10:37:44.884962+03:00")

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
        suppliers_identifier_legal_name = "first_name"
        tender_procuring_entity_name = 'name55555'
        subcontracting_details = "Київ, вул. Островського, 3"
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
                            ),
                            identifier=dict(
                                scheme="UA-EDR",
                                id="00137256",
                                legalName=suppliers_identifier_legal_name
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
                dict(
                    id="1111",
                    lotValues=[dict(relatedLot="11111", value=12)],
                    tenderers=[],
                ),
                dict(
                    id="2222",
                    lotValues=[dict(
                        relatedLot="22222",
                        value=15,
                        subcontractingDetails=subcontracting_details
                    ),],
                    tenderers=[
                        dict(
                            name='name2',
                            identifier=dict(
                                scheme="UA-EDR",
                                id="00137256",
                                legalName="some_legal_name2"
                            )
                        ),
                    ],
                ),
                dict(
                    id="3333", lotValues=[dict(relatedLot="22222", value=20)],
                    tenderers=[
                        dict(
                            name='name3',
                            identifier=dict(
                                scheme="UA-EDR",
                                id="333333",
                            )
                        ),
                    ],
                ),
                dict(
                    id="4444",
                    status="deleted",
                    tenderers=[],
                ),
                dict(
                    id="77777",
                    status="invalid",
                    tenderers=[],
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
                dict(
                    relatedLot="22222",
                    deliveryAddress=dict(
                        countryName="Україна",
                        streetAddress="вул. Банкова 1",
                        region="м. Київ"
                    )
                ),
            ],
            procuringEntity=dict(
                identifier=dict(
                    scheme="UA-EDR",
                    id="00137256",
                ),
                name=tender_procuring_entity_name,
                kind="general",
            ),
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
        expected_items = [{
            'relatedLot': '22222',
            'deliveryAddress': {
                'countryName': 'Україна',
                'region': 'м. Київ',
                'streetAddress': 'вул. Банкова 1'
            },
            'item_delivery_address': "Україна, м. Київ, вул. Банкова 1"
        }]
        self.assertEqual(result["tender"]["items"], expected_items)
        self.assertEqual(result["tender"]["milestones"], tender["milestones"][1:])
        expected_bids = [
            {
                'id': '2222',
                'lotValues': [{
                    'relatedLot': '22222',
                    'value': 15,
                    'subcontractingDetails': subcontracting_details
                }],
                'value': 15,
                'tenderers': [
                    {
                        'name': 'name2',
                        'identifier': {'scheme': 'UA-EDR', 'id': '00137256', 'legalName': 'some_legal_name2'}
                    }
                ],
                'award_qualified_eligible': None,
                'bid_suppliers_identifier_name': 'some_legal_name2'
            },
            {
                'id': '3333',
                'lotValues': [{'relatedLot': '22222', 'value': 20}],
                'value': 20,
                'tenderers': [
                    {
                        'name': 'name3',
                        'identifier': {'scheme': 'UA-EDR', 'id': '333333'}
                    }
                ],
                'award_qualified_eligible': None,
                'bid_suppliers_identifier_name': 'name3'
            },
        ]
        self.assertEqual(result["tender"]["bids"], expected_bids)
        self.assertEqual(result["tender_bid"], expected_bids[0])
        self.assertEqual(result["secondary_data"]["award_complaint_period_start_date"], complaint_period_start_date)
        self.assertEqual(result["secondary_data"]["tender_start_date"], tender_start_date)
        expected_contracts_suppliers_address = "Україна, Дніпропетровська область, м. Дніпро, вул. Андрія Фабра, 4, 4 поверх"
        self.assertEqual(
            result["secondary_data"]["contracts_suppliers_address"], expected_contracts_suppliers_address
        )
        self.assertEqual(
            result["secondary_data"]["contracts_suppliers_identifier_name"], suppliers_identifier_legal_name
        ),
        self.assertEqual(
            result["secondary_data"]["tender_procuring_entity_name"], tender_procuring_entity_name
        )
        self.assertEqual(
            result["secondary_data"]["bid_subcontracting_details"], subcontracting_details
        )
        self.assertEqual(
            result["secondary_data"]["procuring_entity_kind"], "general"
        )
        self.assertEqual(result["tender_contract"], tender["contracts"][1])
        self.assertEqual(result["cancellation"], tender["cancellations"][0])
        self.assertEqual(result["lot"], tender["lots"][1])

    def test_prepare_context_without_tender_bids(self):
        task = Mock()
        enquiry_period_start_date = "2019-03-26T14:20:07.813257+03:00"
        complaint_period_start_date = "2020-08-13T14:57:56.498745+03:00"
        suppliers_identifier_name = 'some_name222'
        contract = dict(id="222", awardID="22")
        plan = dict(id="1243455")

        tender = dict(
            procurementMethodType="aboveThresholdUA",
            procuringEntity=dict(
                kind="general",
                identifier=dict(
                    scheme="UA-EDR",
                    id="02141331",
                    legalName="Відділ освіти Іллінецької районної державної адміністрації"
                )
            ),
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
                            ),
                            identifier=dict(
                                scheme="UA-EDR",
                                id="00137256",
                            ),
                            name=suppliers_identifier_name
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

        expected_items = [{'relatedLot': '22222', 'item_delivery_address': None}]
        self.assertEqual(result["tender"]["items"], expected_items)
        self.assertEqual(result["tender"]["milestones"], tender["milestones"][1:])
        self.assertEqual(result["secondary_data"]["award_complaint_period_start_date"], complaint_period_start_date)
        self.assertEqual(result["secondary_data"]["tender_start_date"], enquiry_period_start_date)

        expected_contracts_suppliers_address = "49000, Україна, Дніпропетровська область, Дніпро, м. Дніпро, вул. Андрія Фабра, 4, 4 поверх"
        self.assertEqual(
            result["secondary_data"]["contracts_suppliers_address"],  expected_contracts_suppliers_address
        )
        self.assertEqual(
            result["secondary_data"]["contracts_suppliers_identifier_name"], suppliers_identifier_name
        ),
        self.assertEqual(
            result["secondary_data"]["tender_procuring_entity_name"], "Відділ освіти Іллінецької районної державної адміністрації"
        )
        self.assertEqual(
            result["secondary_data"]["bid_subcontracting_details"], None
        )
        self.assertEqual(
            result["secondary_data"]["procuring_entity_kind"], None
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
        # 1
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

        result = get_custom_address_string(tender_contract.get("suppliers")[0]["address"])
        expected_result = "21100, Україна, Вінницька область, Вінниця, вул. Данила Галицького, буд. 27, каб. 21"
        self.assertEqual(result, expected_result)

        # 2
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
        result = get_custom_address_string(tender_contract.get("suppliers")[0]["address"])
        expected_result = "Україна, Вінницька область, Вінниця"
        self.assertEqual(result, expected_result)

        # 3
        tender_contract = {
            "description": "Послуги шкільних їдалень",
            "items": [
                {
                    "deliveryAddress": {
                        "postalCode": "79000",
                        "countryName": "Україна",
                        "streetAddress": "вул. Банкова 1",
                        "locality": "м. Київ"
                    },
                }
            ]
        }
        result = get_custom_address_string(tender_contract.get("items")[0].get("deliveryAddress"))
        expected_result = "79000, Україна, м. Київ, вул. Банкова 1"
        self.assertEqual(result, expected_result)

        # 4
        tender_contract = {
            "description": "Послуги шкільних їдалень",
            "items": [
                {
                    "some_key": {'aaa': 123},
                }
            ]
        }
        result = get_custom_address_string(tender_contract.get("items")[0].get("deliveryAddress"))
        self.assertEqual(result, None)

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
                    "bidID": 1234,
                },
                {
                    "status": "active",
                    "bidID": bid_id,
                }
            ]
        }

        result = get_award_qualified_eligible(tender, bid)
        self.assertEqual(result, True)

        tender["qualifications"][1]["bidID"] = "999999999"
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

        # 5
        award["status"] = "unsuccessful"
        del award["title"]
        award["description"] = "description1"
        result = handle_award_qualified_eligible_statuses(award)
        self.assertEqual(result, " description1")

        # 6
        del award["description"]
        result = handle_award_qualified_eligible_statuses(award)
        self.assertEqual(result, " ")

    def test_get_name_from_organization(self):
        # 1
        organization = {
            "identifier": {
                "scheme": "UA-EDR",
                "id": "00137256",
                "legalName": "5678_legalName"
            },
            "name": "Тестове підприємство",
        }
        result = get_name_from_organization(organization)
        self.assertEqual(result, "5678_legalName")

        # 2
        organization = {
            "identifier": {
                "scheme": "UA-EDR",
                "id": "00137256",
            },
            "name": "Тестове підприємство",
        }
        result = get_name_from_organization(organization)
        self.assertEqual(result, "Тестове підприємство")

        # 3
        organization = {}
        result = get_name_from_organization(organization)
        self.assertEqual(result, None)

    def test_get_bid_subcontracting_details(self):
        # 1
        tender_award = {
            "status": "active",
            "lotID": "33333333333333333",
            "bid_id": "222222222222222",
            "id": "11111111111111"
        }

        tender_bid = {
            "status": "active",
            "lotValues": [],
            "id": "222222222222222",
        }

        related_lot = "33333333333333333"

        tender = {
            "procurementMethodType": "aboveThresholdEU",
            "contracts": [
                {
                    "awardID": "11111111111111",
                    "id": "0d66ea8da72649d4baf5d7a7d00109e6",
                },
                {
                    "awardID": "d0824888bb964f56bf761fdc667e8739",
                    "id": "b303009e230b40c2a4b1c215a704492d",
                }
            ],
            "lots": []
        }

        result = get_bid_subcontracting_details(tender_award, tender_bid, related_lot, tender)
        self.assertEqual(result, None)

        # 2
        tender_bid["lotValues"] = [
            {
                "relatedLot": "dd22c9c085f64e019f943999b5b41fe5",
                "subcontractingDetails": "Тестове підприємство, Україна"
            },
            {
                "relatedLot": "33333333333333333",
                "subcontractingDetails": "Підприємство 2, Київ, Україна"
            }
        ]

        result = get_bid_subcontracting_details(tender_award, tender_bid, related_lot, tender)
        self.assertEqual(result, "Підприємство 2, Київ, Україна")

        # 3

        tender = {
            "procurementMethodType": "negotiation.quick",
        }
        tender_award = {
            "id": "12345",
            "subcontractingDetails": "тест, вул. Островського, 3"
        }

        result = get_bid_subcontracting_details(tender_award, {}, None, tender)
        self.assertEqual(result, "тест, вул. Островського, 3")

        # 4
        tender = {
            "procurementMethodType": "tender_without_lots"
        }

        tender_bid = {
            "id": "12345",
            "subcontractingDetails": "тест, вул. Шевченка, 3"
        }

        result = get_bid_subcontracting_details({}, tender_bid, None, tender)
        self.assertEqual(result, "тест, вул. Шевченка, 3")

    def test_get_procuring_entity_kind(self):
        # 1
        tender_start_date = "2020-04-18T10:34:42.821494+03:00"
        result = get_procuring_entity_kind(tender_start_date, tender={})
        self.assertEqual(result, None)

        # 2
        result = get_procuring_entity_kind(tender_start_date=None, tender={})
        self.assertEqual(result, None)

        # 3
        tender = {
            "procuringEntity": {
                "kind": "general"
            },
            "id": "1234567"
        }
        result = get_procuring_entity_kind(tender_start_date, tender)
        self.assertEqual(result, None)

        # 4
        tender_start_date = "2020-06-15T10:34:42.821494+03:00"
        result = get_procuring_entity_kind(tender_start_date, tender)
        self.assertEqual(result, "general")

        # 5
        del tender["procuringEntity"]["kind"]
        result = get_procuring_entity_kind(tender_start_date, tender)
        self.assertEqual(result, None)
