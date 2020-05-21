# -*- coding: utf-8 -*-

from treasury.templates import render_catalog_xml, render_change_xml, render_contract_xml, \
    prepare_context, prepare_contract_context
from unittest.mock import Mock, patch
from environment_settings import TIMEZONE
from copy import deepcopy
from datetime import datetime
import unittest

test_changes = [
    dict(
        id="234",
        contractNumber="1",
        contractID="1",
        rationale="things change",
        rationaleTypes=["first", "second"],
        dateSigned=datetime(2012, 2, 3, 4, 5, 6, tzinfo=TIMEZONE),
        documents="ham="
    ),
    dict(
        id="567",
        contractNumber="2",
        rationale="dunno",
        rationaleTypes=["third"],
        dateSigned=datetime(2007, 5, 6),
        documents="meat="
    )
]
test_contract = dict(
    id="123",
    contractNumber="78",
    period=dict(
        startDate=datetime(2001, 12, 1),
        endDate=datetime(2021, 12, 31),
    ),
    value=dict(
        amount=12,
        currency="slaves",
        amountNet=13,
    ),
    dateSigned=datetime(2001, 12, 3),
    documents="spam=",
    changes=test_changes,
)
test_classification = dict(
    id="678",
    scheme="UA_EBR",
    description="Banana"
)
test_add_classifications = [
    dict(
        id="12",
        scheme="UA_W",
        description="green banana"
    ),
    dict(
        id="2",
        scheme="ISO-666",
        description="edible stuff"
    )
]
test_plan = dict(
    id="999",
    procuringEntity=dict(
        name="My name",
        identifier=dict(
            id="99999-99",
        )
    ),
    classification=test_classification,
    additionalClassifications=test_add_classifications,
    budget=dict(
        description="Budget",
        amount=500,
        currency="UAU",
        amountNet=550,
        breakdown=[
            dict(
                id=1,
                title="first b",
                description="...b",
                value=dict(amount=200)
            ),
            dict(
                id=2,
                title="second b",
                description="...c",
                value=dict(amount=300)
            )
        ],
    ),
    tender=dict(
        tenderPeriod=dict(
            startDate=datetime(1990, 1, 1, 12, 30)
        ),
        procurementMethodType="belowAbove"
    ),

)
test_tender = dict(
    id="55555",
    date=datetime(2006, 5, 7),
    procuringEntity=dict(
        name="My name",
        identifier=dict(
            id="99999-99",
        )
    ),
    mainProcurementCategory="good goods",
    items=[
        dict(
            id="11",
            description="bla",
            classification=test_classification,
            additionalClassifications=test_add_classifications,
            quantity=2,
            unit=dict(name="FF"),
            deliveryAddress=dict(city="Kharkiv", street="Turbo-atom"),
            deliveryDate=dict(endDate=datetime(1999, 12, 12)),
        ),
        dict(
            id="222",
            description="bla bla",
            classification=test_classification,
            additionalClassifications=[],
            quantity=3,
            unit=dict(name="FFA"),
        )
    ],
    milestones=[
        dict(
            id="122",
            title="122 title",
            description="122 description",
            code="122 code",
            percentage=30,
            duration=dict(days=12, type="business"),
        ),
        dict(
            id="222",
            title="222 title",
            description="222 description",
            code="222 code",
            percentage=70,
            duration=dict(days=22, type="sunny"),
        )
    ],
    bids=[
        dict(
            id="1",
            tenderers=[dict(identifier=dict(legalName="My name"))],
            selfQualified=True,
            value=dict(amount=123)
        ),
        dict(
            id="2",
            tenderers=[dict(identifier=dict(legalName="his name"))],
            selfQualified=False,
            value=dict(amount=321)
        )
    ],
)
test_initial_bids = {"1": 333, "2": 555}
test_tender_award = dict(complaintPeriod=dict(startDate=datetime(2012, 4, 1)))
test_tender_contract = dict(
    id="123",
    value=dict(
        amount=12,
    ),
    suppliers=[
        dict(
            identifier=dict(legalName="his name"),
            address=dict(stree="Street, 1", city="Kyiv"),
        )
    ],
    dateSigned=datetime(2001, 12, 3),
)


class TemplatesTestCase(unittest.TestCase):

    def test_catalog(self):
        context = dict(catalog_id="YourMomBFs")
        result = render_catalog_xml(context)
        self.assertEqual(
            result,
            b'<?xml version="1.0" encoding="windows-1251"?>'
            b'<root method_name="GetRef">'
            b'<ref id="YourMomBFs" date="">'
            b'</ref>'
            b'</root>'
        )

    def test_catalog_with_date(self):
        context = dict(catalog_id="YourGFs", since_date=datetime(2007, 5, 1, 0, 0, 3))
        result = render_catalog_xml(context)
        self.assertEqual(
            result,
            b'<?xml version="1.0" encoding="windows-1251"?>'
            b'<root method_name="GetRef">'
            b'<ref id="YourGFs" date="2007-05-01T00:00:03">'
            b'</ref>'
            b'</root>'
        )

    def test_catalog_encoding(self):
        context = dict(catalog_id="Список твоих косяков", since_date=datetime(2007, 5, 1, 0, 0, 3))
        result = render_catalog_xml(context)

        with open("treasury/tests/fixtures/request_catalog_encoding.xml", "rb") as f:
            self.assertEqual(result, f.read())

    def test_change(self):
        context = dict(
            contract=test_contract,
            change=test_changes[0],
        )
        result = render_change_xml(context)
        self.assertEqual(
            result,
            b'<?xml version="1.0" encoding="windows-1251"?>'
            b'<root method_name="PrChange">'
            b'<contractId>123</contractId>'
            b'<contractsDateSigned>2001-12-03T00:00:00</contractsDateSigned>'
            b'<contractsValueAmount>12</contractsValueAmount>'
            b'<contractsValueCurrency>slaves</contractsValueCurrency>'
            b'<contractsValueAmountNet>13</contractsValueAmountNet>'
            b'<changeId>234</changeId>'
            b'<changeContractNumber>1</changeContractNumber>'
            b'<changeRationale>things change</changeRationale>'
            b'<changeRationaleTypes>first, second</changeRationaleTypes>'
            b'<DateSigned>2012-02-03T04:05:06</DateSigned>'
            b'<changeDocuments>ham=</changeDocuments>'
            b'</root>'
        )

    def test_contract_max(self):
        context = dict(
            contract=test_contract,
            plan=test_plan,
            tender=test_tender,
            tender_bid=test_tender["bids"][0],
            tender_award=test_tender_award,
            tender_contract=test_tender_contract,
            cancellation={},
            initial_bids=test_initial_bids,
        )
        result = render_contract_xml(context)
        self.assertEqual(
            result,
            b'<?xml version="1.0" encoding="windows-1251"?>'
            b'<root method_name="PrContract">'
            b'<contract>'
            b'<contractId>123</contractId>'
            b'<contractNumber>78</contractNumber>'
            b'<contractsPeriodStartDate>2001-12-01T00:00:00</contractsPeriodStartDate>'
            b'<contractsPeriodEndDate>2021-12-31T00:00:00</contractsPeriodEndDate>'
            b'<contractsValueAmount>12</contractsValueAmount>'
            b'<contractsValueCurrency>slaves</contractsValueCurrency>'
            b'<contractsValueAmountNet>13</contractsValueAmountNet>'
            b'<contractsDateSigned>2001-12-03T00:00:00</contractsDateSigned>'
            b'<contractsDocuments>spam=</contractsDocuments>'
            b'</contract>'
            b'<changes>'
            b'<change>'
            b'<changeId>234</changeId>'
            b'<contractNumber>1</contractNumber>'
            b'<changeRationale>things change</changeRationale>'
            b'<changeRationaleTypes>first, second</changeRationaleTypes>'
            b'<contractsDateSigned>2012-02-03T04:05:06</contractsDateSigned>'
            b'<changeDocuments>ham=</changeDocuments>'
            b'</change>'
            b'<change>'
            b'<changeId>567</changeId>'
            b'<contractNumber>2</contractNumber>'
            b'<changeRationale>dunno</changeRationale>'
            b'<changeRationaleTypes>third</changeRationaleTypes>'
            b'<contractsDateSigned>2007-05-06T00:00:00</contractsDateSigned>'
            b'<changeDocuments>meat=</changeDocuments>'
            b'</change></changes>'
            b'<plan>'
            b'<planId>999</planId>'
            b'<procuringEntityName>My name</procuringEntityName>'
            b'<procuringEntityIdentifierId>99999-99</procuringEntityIdentifierId>'
            b'<classificationId>678</classificationId>'
            b'<classificationDescription>Banana</classificationDescription>'
            b'<additionalClassifications>'
            b'<additionalClassification>'
            b'<additionalClassificationsScheme>UA_W</additionalClassificationsScheme>'
            b'<additionalClassificationsId>12</additionalClassificationsId>'
            b'<additionalClassificationsDescription>green banana</additionalClassificationsDescription>'
            b'</additionalClassification>'
            b'<additionalClassification>'
            b'<additionalClassificationsScheme>ISO-666</additionalClassificationsScheme>'
            b'<additionalClassificationsId>2</additionalClassificationsId>'
            b'<additionalClassificationsDescription>edible stuff</additionalClassificationsDescription>'
            b'</additionalClassification></additionalClassifications>'
            b'<budgetDescription>Budget</budgetDescription>'
            b'<budgetAmount>500</budgetAmount>'
            b'<budgetCurrency>UAU</budgetCurrency>'
            b'<budgetAmountNet>550</budgetAmountNet>'
            b'<tenderPeriodStartDate>1990-01-01T12:30:00</tenderPeriodStartDate>'
            b'<tenderProcurementMethodType>belowAbove</tenderProcurementMethodType>'
            b'<breakdowns>'
            b'<breakdown>'
            b'<breakdownId>1</breakdownId>'
            b'<breakdownTitle>first b</breakdownTitle>'
            b'<breakdownDescription>...b</breakdownDescription>'
            b'<breakdownAmount>200</breakdownAmount>'
            b'</breakdown>'
            b'<breakdown>'
            b'<breakdownId>2</breakdownId>'
            b'<breakdownTitle>second b</breakdownTitle>'
            b'<breakdownDescription>...c</breakdownDescription>'
            b'<breakdownAmount>300</breakdownAmount>'
            b'</breakdown></breakdowns>'
            b'</plan>'
            b'<report>'
            b'<tenderID>55555</tenderID>'
            b'<date>2006-05-07T00:00:00</date>'
            b'<procuringEntityName>My name</procuringEntityName>'
            b'<procuringEntityIdentifierId>99999-99</procuringEntityIdentifierId>'
            b'<mainProcurementCategory>good goods</mainProcurementCategory>'
            b'<items>'
            b'<item>'
            b'<itemsId>11</itemsId>'
            b'<itemsDescription>bla</itemsDescription>'
            b'<itemsClassificationScheme>UA_EBR</itemsClassificationScheme>'
            b'<itemsClassificationId>678</itemsClassificationId>'
            b'<itemsClassificationDescription>Banana</itemsClassificationDescription>'
            b'<itemsAdditionalClassifications>'
            b'<itemsAdditionalClassification>'
            b'<itemsAdditionalClassificationsScheme>UA_W</itemsAdditionalClassificationsScheme>'
            b'<itemsAdditionalClassificationsId>12</itemsAdditionalClassificationsId>'
            b'<itemsAdditionalClassificationsDescription>green banana</itemsAdditionalClassificationsDescription>'
            b'</itemsAdditionalClassification>'
            b'<itemsAdditionalClassification>'
            b'<itemsAdditionalClassificationsScheme>ISO-666</itemsAdditionalClassificationsScheme>'
            b'<itemsAdditionalClassificationsId>2</itemsAdditionalClassificationsId>'
            b'<itemsAdditionalClassificationsDescription>edible stuff</itemsAdditionalClassificationsDescription>'
            b'</itemsAdditionalClassification></itemsAdditionalClassifications>'
            b'<itemsQuantity>2</itemsQuantity>'
            b'<itemsUnitName>FF</itemsUnitName>'
            b'<itemsDeliveryAddress>Kharkiv, Turbo-atom</itemsDeliveryAddress>'
            b'<itemsDeliveryDateEndDate>1999-12-12T00:00:00</itemsDeliveryDateEndDate>'
            b'</item>'
            b'<item>'
            b'<itemsId>222</itemsId>'
            b'<itemsDescription>bla bla</itemsDescription>'
            b'<itemsClassificationScheme>UA_EBR</itemsClassificationScheme>'
            b'<itemsClassificationId>678</itemsClassificationId>'
            b'<itemsClassificationDescription>Banana</itemsClassificationDescription>'
            b'<itemsQuantity>3</itemsQuantity>' 
            b'<itemsUnitName>FFA</itemsUnitName>'
            b'</item></items>'
            b'<milestones>'
            b'<milestone>'
            b'<milestonesId>122</milestonesId>'
            b'<milestonesTitle>122 title</milestonesTitle>'
            b'<milestonesDescription>122 description</milestonesDescription>'
            b'<milestonesCode>122 code</milestonesCode>'
            b'<milestonesDurationDays>12</milestonesDurationDays>'
            b'<milestonesDurationType>business</milestonesDurationType>'
            b'<milestonesPercentage>30</milestonesPercentage>'
            b'</milestone>'
            b'<milestone>'
            b'<milestonesId>222</milestonesId>'
            b'<milestonesTitle>222 title</milestonesTitle>'
            b'<milestonesDescription>222 description</milestonesDescription>'
            b'<milestonesCode>222 code</milestonesCode>'
            b'<milestonesDurationDays>22</milestonesDurationDays>'
            b'<milestonesDurationType>sunny</milestonesDurationType>'
            b'<milestonesPercentage>70</milestonesPercentage>'
            b'</milestone></milestones>'
            b'<startDate>2012-04-01T00:00:00</startDate>'
            b'<bids>'
            b'<bid>'
            b'<bidsId>1</bidsId>'
            b'<bidsSuppliersIdentifierName>My name</bidsSuppliersIdentifierName>'
            b'<bidsValueAmount>333</bidsValueAmount>'
            b'<bidsValueAmountLast>123</bidsValueAmountLast>'
            b'<awardQualifiedEligible>True</awardQualifiedEligible>'
            b'</bid>'
            b'<bid>'
            b'<bidsId>2</bidsId>'
            b'<bidsSuppliersIdentifierName>his name</bidsSuppliersIdentifierName>'
            b'<bidsValueAmount>555</bidsValueAmount>'
            b'<bidsValueAmountLast>321</bidsValueAmountLast>'
            b'<awardQualifiedEligible>False</awardQualifiedEligible>'
            b'</bid></bids>'
            b'<awardComplaintPeriodStartDate>2012-04-01T00:00:00</awardComplaintPeriodStartDate>'
            b'<contractsDateSigned>2001-12-03T00:00:00</contractsDateSigned>'
            b'<contractsSuppliersIdentifierName>his name</contractsSuppliersIdentifierName>'
            b'<contractsSuppliersAddress>Street, 1, Kyiv</contractsSuppliersAddress>'
            b'<ContractsValueAmount>12</ContractsValueAmount>'
            b'<ContractsContractID>123</ContractsContractID>'
            b'</report>'
            b'</root>'
        )

    def test_contract_min(self):
        context = dict(
            contract=test_contract,
            plan=test_plan,
            tender=test_tender,
            tender_bid=test_tender["bids"][0],
            tender_award=test_tender_award,
            tender_contract=test_tender_contract,
            cancellation={},
            initial_bids=test_initial_bids,
        )
        context = deepcopy(context)
        del context["contract"]["period"]
        del context["contract"]["value"]
        context["contract"]["changes"] = []
        del context["plan"]["additionalClassifications"]
        del context["plan"]["budget"]
        context["tender"]["items"] = []
        context["tender"]["milestones"] = []
        context["tender"]["bids"] = []
        result = render_contract_xml(context)
        self.assertEqual(
            result,
            b'<?xml version="1.0" encoding="windows-1251"?>'
            b'<root method_name="PrContract">'
            b'<contract>'
            b'<contractId>123</contractId>'
            b'<contractNumber>78</contractNumber>'
            b'<contractsDateSigned>2001-12-03T00:00:00</contractsDateSigned>'
            b'<contractsDocuments>spam=</contractsDocuments>'
            b'</contract>'
            b'<plan>'
            b'<planId>999</planId>'
            b'<procuringEntityName>My name</procuringEntityName>'
            b'<procuringEntityIdentifierId>99999-99</procuringEntityIdentifierId>'
            b'<classificationId>678</classificationId>'
            b'<classificationDescription>Banana</classificationDescription>'
            b'<tenderPeriodStartDate>1990-01-01T12:30:00</tenderPeriodStartDate>'
            b'<tenderProcurementMethodType>belowAbove</tenderProcurementMethodType>'
            b'</plan>'
            b'<report>'
            b'<tenderID>55555</tenderID>'
            b'<date>2006-05-07T00:00:00</date>'
            b'<procuringEntityName>My name</procuringEntityName>'
            b'<procuringEntityIdentifierId>99999-99</procuringEntityIdentifierId>'
            b'<mainProcurementCategory>good goods</mainProcurementCategory>'
            b'<startDate>2012-04-01T00:00:00</startDate>'
            b'<awardComplaintPeriodStartDate>2012-04-01T00:00:00</awardComplaintPeriodStartDate>'
            b'<contractsDateSigned>2001-12-03T00:00:00</contractsDateSigned>'
            b'<contractsSuppliersIdentifierName>his name</contractsSuppliersIdentifierName>'
            b'<contractsSuppliersAddress>Street, 1, Kyiv</contractsSuppliersAddress>'
            b'<ContractsValueAmount>12</ContractsValueAmount>'
            b'<ContractsContractID>123</ContractsContractID>'
            b'</report>'
            b'</root>'
        )

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

        with patch("treasury.templates.prepare_contract_context") as prepare_contract_mock:
            with patch("treasury.templates.download_file") as download_file_mock:
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


