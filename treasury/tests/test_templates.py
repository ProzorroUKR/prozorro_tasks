# -*- coding: utf-8 -*-

from treasury.templates import (
    render_catalog_xml, render_change_xml, render_contract_xml,
    format_date, render_transactions_confirmation_xml,
)
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
        dateSigned=datetime(2012, 2, 3, 4, 5, 6),
        documents=[]
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
    procuring_entity_name='My name',
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
    title="Distribution of natural gas for SZRU",
    tenderID="UA-2020-55555",
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
            item_delivery_address="Kiev, Shevchenko Street, 5"
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
            value=dict(amount=123),
            subcontractingDetails="DKP Book, Ukraine Lviv",
            award_qualified_eligible=True,
            bid_suppliers_identifier_name='Bid_Suppliers_Identifier_Name12345'
        ),
        dict(
            id="2",
            tenderers=[dict(identifier=dict(legalName="his name"))],
            selfQualified=False,
            value=dict(amount=321),
            subcontractingDetails="Will not be used",
            award_qualified_eligible=None,
            bid_suppliers_identifier_name='Bid_Suppliers_Identifier_Name67890'
        )
    ],
)
test_initial_bids = {"1": 333, "2": 555}
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
    dateSigned="2020-03-11T00:00:00+05:00",
)

test_lot = dict(
    status="complete",
    title="Lot 1, Some lot information",
    date="2018-04-18T13:09:54.997464+03:00"
)

test_secondary_data = dict(
    tender_start_date="2020-07-27T13:09:54.997464+03:00",
    award_complaint_period_start_date="2020-08-14T12:32:18.080119+03:00",
    contracts_suppliers_address="Ukraine, Dnipro, Shevchenko Street, 4",
    contracts_suppliers_identifier_name="contractSupplierName12345",
    tender_procuring_entity_name="TenderProcurementEntityName555555",
    bid_subcontracting_details="DKP Book, Ukraine Lviv",
    procuring_entity_kind="general"
)


class TemplatesTestCase(unittest.TestCase):

    def test_format_date(self):
        result = format_date("2020-03-11T00:00:00+02:00")
        self.assertEqual(result, "2020-03-11T00:00:00+02:00")

        result = format_date("2020-03-11T01:02:30")
        self.assertEqual(result, "2020-03-11T01:02:30")

        result = format_date("2020-03-11T01:02:30+05:00")
        self.assertEqual(result, "2020-03-11T01:02:30+05:00")

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
            b'</root>'
        )

    def test_contract_max(self):
        context = dict(
            contract=test_contract,
            plan=test_plan,
            tender=test_tender,
            tender_bid=test_tender["bids"][0],
            tender_contract=test_tender_contract,
            cancellation={},
            initial_bids=test_initial_bids,
            lot=test_lot,
            secondary_data=test_secondary_data,
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
            b'<tenderID>UA-2020-55555</tenderID>'
            b'<date>2018-04-18T13:09:54.997464+03:00</date>'
            b'<procuringEntityName>TenderProcurementEntityName555555</procuringEntityName>'
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
            b'<itemsDeliveryAddress>Kiev, Shevchenko Street, 5</itemsDeliveryAddress>'
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
            b'<startDate>2020-07-27T13:09:54.997464+03:00</startDate>'
            b'<bids>'
            b'<bid>'
            b'<bidsId>1</bidsId>'
            b'<bidsSuppliersIdentifierName>Bid_Suppliers_Identifier_Name12345</bidsSuppliersIdentifierName>'
            b'<bidsValueAmount>333</bidsValueAmount>'
            b'<bidsValueAmountLast>123</bidsValueAmountLast>'
            b'<awardQualifiedEligible>True</awardQualifiedEligible>'
            b'</bid>'
            b'<bid>'
            b'<bidsId>2</bidsId>'
            b'<bidsSuppliersIdentifierName>Bid_Suppliers_Identifier_Name67890</bidsSuppliersIdentifierName>'
            b'<bidsValueAmount>555</bidsValueAmount>'
            b'<bidsValueAmountLast>321</bidsValueAmountLast>'
            b'</bid></bids>'
            b'<awardComplaintPeriodStartDate>2020-08-14T12:32:18.080119+03:00</awardComplaintPeriodStartDate>'
            b'<contractsDateSigned>2020-03-11T00:00:00+05:00</contractsDateSigned>'
            b'<contractsSuppliersIdentifierName>contractSupplierName12345</contractsSuppliersIdentifierName>'
            b'<contractsSuppliersAddress>Ukraine, Dnipro, Shevchenko Street, 4</contractsSuppliersAddress>'
            b'<bidSubcontractingDetails>DKP Book, Ukraine Lviv</bidSubcontractingDetails>'
            b'<ContractsValueAmount>12</ContractsValueAmount>'
            b'<ContractsContractID>123</ContractsContractID>'
            b'<lotsTitle>Lot 1, Some lot information</lotsTitle>'
            b'<procuringEntityKind>general</procuringEntityKind>'
            b'<tendersTitle>Distribution of natural gas for SZRU</tendersTitle>'
            b'</report>'
            b'</root>'
        )

    def test_contract_min(self):
        context = dict(
            contract=test_contract,
            plan=test_plan,
            tender=test_tender,
            tender_bid={},
            tender_contract=test_tender_contract,
            cancellation={},
            initial_bids={},
            secondary_data=test_secondary_data,
        )
        context = deepcopy(context)
        del context["contract"]["period"]
        del context["contract"]["value"]
        context["contract"]["changes"] = []
        del context["plan"]["additionalClassifications"]
        del context["plan"]["budget"]
        del context["tender"]["title"]
        context["tender"]["items"] = []
        context["tender"]["milestones"] = []
        context["tender"]["bids"] = []
        context["secondary_data"]["procuring_entity_kind"] = None
        result = render_contract_xml(context)

        expected_result = (
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
            b'<tenderID>UA-2020-55555</tenderID>'
            b'<date>2006-05-07T00:00:00</date>'
            b'<procuringEntityName>TenderProcurementEntityName555555</procuringEntityName>'
            b'<procuringEntityIdentifierId>99999-99</procuringEntityIdentifierId>'
            b'<mainProcurementCategory>good goods</mainProcurementCategory>'
            b'<startDate>2020-07-27T13:09:54.997464+03:00</startDate>'
            b'<awardComplaintPeriodStartDate>2020-08-14T12:32:18.080119+03:00</awardComplaintPeriodStartDate>'
            b'<contractsDateSigned>2020-03-11T00:00:00+05:00</contractsDateSigned>'
            b'<contractsSuppliersIdentifierName>contractSupplierName12345</contractsSuppliersIdentifierName>'
            b'<contractsSuppliersAddress>Ukraine, Dnipro, Shevchenko Street, 4</contractsSuppliersAddress>'
            b'<bidSubcontractingDetails>DKP Book, Ukraine Lviv</bidSubcontractingDetails>'
            b'<ContractsValueAmount>12</ContractsValueAmount>'
            b'<ContractsContractID>123</ContractsContractID>'
            b'</report>'
            b'</root>'
        )

        self.assertEqual(
            result,
            expected_result
        )

        del context["contract"]["changes"]
        result = render_contract_xml(context)
        self.assertEqual(
            result,
            expected_result
        )

    def test_build_transactions_result_xml(self):
        params = dict(
            register_id='123',
            status_id='456',
            date=datetime(2015, 2, 3, 4, 5, 6).isoformat(),
            rec_count=5,
            reg_sum=45600000.25,
        )
        result = render_transactions_confirmation_xml(**params)
        expected_result = (
            b'<?xml version="1.0" encoding="windows-1251"?>'
            b'<root method_name="ConfirmPRTrans">'
            b'<register_id>123</register_id>'
            b'<status_id>456</status_id>'
            b'<date>2015-02-03T04:05:06</date>'
            b'<rec_count>5</rec_count>'
            b'<reg_sum>45600000.25</reg_sum>'
            b'</root>'
        )

        self.assertEqual(result, expected_result)


