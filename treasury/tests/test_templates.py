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
            deliveryAddress=dict(city="Kharkiv", street="Nauki, 23"),
            deliveryDate=dict(endDate=datetime(1999, 12, 22)),
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
            b'<?xml version="1.0" encoding="windows-1251"?>\n'
            b'<root method_name="GetRef">\n'
            b'    <ref id="YourMomBFs" date="">\n'
            b'    </ref>\n'
            b'</root>'
        )

    def test_catalog_with_date(self):
        context = dict(catalog_id="YourGFs", since_date=datetime(2007, 5, 1, 0, 0, 3))
        result = render_catalog_xml(context)
        self.assertEqual(
            result,
            b'<?xml version="1.0" encoding="windows-1251"?>\n'
            b'<root method_name="GetRef">\n'
            b'    <ref id="YourGFs" date="2007-05-01T00:00:03">\n'
            b'    </ref>\n'
            b'</root>'
        )

    def test_change(self):
        context = dict(
            contract=test_contract,
            change=test_changes[0],
        )
        result = render_change_xml(context)
        self.assertEqual(
            result,
            b'<?xml version="1.0" encoding="windows-1251"?>\n'
            b'<root method_name="PrChange">\n'
            b'    <contractId>123</contractId>\n'
            b'    <contractsDateSigned>2001-12-03T00:00:00</contractsDateSigned>\n'
            b'    <contractsValueAmount>12</contractsValueAmount>\n'
            b'    <contractsValueCurrency>slaves</contractsValueCurrency>\n'
            b'    <contractsValueAmountNet>13</contractsValueAmountNet>\n'
            b'    <changeId>234</changeId>\n'
            b'    <changeContractNumber>1</changeContractNumber>\n'
            b'    <changeRationale>things change</changeRationale>\n'
            b'    <changeRationaleTypes>first, second</changeRationaleTypes>\n'
            b'    <DateSigned>2012-02-03T04:05:06</DateSigned>\n'
            b'    <changeDocuments>ham=</changeDocuments>\n'
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
            b'<?xml version="1.0" encoding="windows-1251"?>\n'
            b'<root method_name="PrContract">\n'
            b'    <contract>\n'
            b'        <contractId>123</contractId>\n'
            b'        <contractNumber></contractNumber>\n'
            b'        <contractsPeriodStartDate>2001-12-01 00:00:00</contractsPeriodStartDate>\n'
            b'        <contractsPeriodEndDate>2021-12-31 00:00:00</contractsPeriodEndDate>\n'
            b'        <contractsValueAmount>12</contractsValueAmount>\n'
            b'        <contractsValueCurrency>slaves</contractsValueCurrency>\n'
            b'        <contractsValueAmountNet>13</contractsValueAmountNet>\n'
            b'        <contractsDateSigned>2001-12-03 00:00:00</contractsDateSigned>\n'
            b'        <contractsDocuments>spam=</contractsDocuments>\n'
            b'    </contract>\n'
            b'    <changes>\n'
            b'        <change>\n'
            b'            <changeId>234</changeId>\n'
            b'            <contractNumber></contractNumber>\n'
            b'            <changeRationale>things change</changeRationale>\n'
            b'            <changeRationaleTypes>first, second</changeRationaleTypes>\n'
            b'            <contractsDateSigned>2012-02-03 04:05:06+02:02</contractsDateSigned>\n'
            b'            <changeDocuments>ham=</changeDocuments>\n'
            b'        </change>\n'
            b'        <change>\n'
            b'            <changeId>567</changeId>\n'
            b'            <contractNumber></contractNumber>\n'
            b'            <changeRationale>dunno</changeRationale>\n'
            b'            <changeRationaleTypes>third</changeRationaleTypes>\n'
            b'            <contractsDateSigned>2007-05-06 00:00:00</contractsDateSigned>\n'
            b'            <changeDocuments>meat=</changeDocuments>\n'
            b'        </change></changes>\n'
            b'    <plan>\n'
            b'    <planId>999</planId>\n'
            b'    <procuringEntityName>My name</procuringEntityName>\n'
            b'    <procuringEntityIdentifierId>99999-99</procuringEntityIdentifierId>\n'
            b'    <classificationId>678</classificationId>\n'
            b'    <classificationDescription>Banana</classificationDescription>\n'
            b'    <additionalClassifications>\n'
            b'        <additionalClassification>\n'
            b'            <additionalClassificationsScheme>UA_W</additionalClassificationsScheme>\n'
            b'            <additionalClassificationsId>12</additionalClassificationsId>\n'
            b'            <additionalClassificationsDescription>green banana</additionalClassificationsDescription>\n'
            b'        </additionalClassification>\n'
            b'        <additionalClassification>\n'
            b'            <additionalClassificationsScheme>ISO-666</additionalClassificationsScheme>\n'
            b'            <additionalClassificationsId>2</additionalClassificationsId>\n'
            b'            <additionalClassificationsDescription>edible stuff</additionalClassificationsDescription>\n'
            b'        </additionalClassification></additionalClassifications>\n'
            b'    <budgetDescription>Budget</budgetDescription>\n'
            b'    <budgetAmount>500</budgetAmount>\n'
            b'    <budgetCurrency>UAU</budgetCurrency>\n'
            b'    <budgetAmountNet>550</budgetAmountNet>\n'
            b'    <tenderPeriodStartDate>1990-01-01 12:30:00</tenderPeriodStartDate>\n'
            b'    <tenderProcurementMethodType>belowAbove</tenderProcurementMethodType>\n'
            b'    <breakdowns>\n'
            b'        <breakdown>\n'
            b'            <breakdownId>1</breakdownId>\n'
            b'            <breakdownTitle>first b</breakdownTitle>\n'
            b'            <breakdownDescription>...b</breakdownDescription>\n'
            b'            <breakdownAmount>200</breakdownAmount>\n'
            b'        </breakdown>\n'
            b'        <breakdown>\n'
            b'            <breakdownId>2</breakdownId>\n'
            b'            <breakdownTitle>second b</breakdownTitle>\n'
            b'            <breakdownDescription>...c</breakdownDescription>\n'
            b'            <breakdownAmount>300</breakdownAmount>\n'
            b'        </breakdown></breakdowns>\n'
            b'</plan>\n'
            b'<report>\n'
            b'    <tenderID>55555</tenderID>\n'
            b'    <date>2006-05-07 00:00:00</date>\n'
            b'    <procuringEntityName>My name</procuringEntityName>\n'
            b'    <procuringEntityIdentifierId>99999-99</procuringEntityIdentifierId>\n'
            b'    <mainProcurementCategory>good goods</mainProcurementCategory>\n'
            b'    <items>\n'
            b'        <item>\n'
            b'            <itemsId>11</itemsId>\n'
            b'            <itemsDescription>bla</itemsDescription>\n'
            b'            <itemsClassificationScheme></itemsClassificationScheme>\n'
            b'            <itemsClassificationId>678</itemsClassificationId>\n'
            b'            <itemsClassificationDescription>Banana</itemsClassificationDescription>\n'
            b'            <itemsAdditionalClassifications>\n'
            b'                <itemsAdditionalClassification>\n'
            b'                    <itemsAdditionalClassificationsScheme>UA_W</itemsAdditionalClassificationsScheme>\n'
            b'                    <itemsAdditionalClassificationsId>12</itemsAdditionalClassificationsId>\n'
            b'                    <itemsAdditionalClassificationsDescription>green banana</itemsAdditionalClassificationsDescription>\n'
            b'                </itemsAdditionalClassification>\n'
            b'                <itemsAdditionalClassification>\n'
            b'                    <itemsAdditionalClassificationsScheme>ISO-666</itemsAdditionalClassificationsScheme>\n'
            b'                    <itemsAdditionalClassificationsId>2</itemsAdditionalClassificationsId>\n'
            b'                    <itemsAdditionalClassificationsDescription>edible stuff</itemsAdditionalClassificationsDescription>\n'
            b'                </itemsAdditionalClassification>\n'
            b'            </itemsAdditionalClassifications>\n'
            b'            <itemsQuantity>2</itemsQuantity>\n'
            b'            <itemsUnitName>FF</itemsUnitName>\n'
            b'            <itemsDeliveryAddress>Kharkiv, Turbo-atom</itemsDeliveryAddress>\n'
            b'            <itemsDeliveryDateEndDate>1999-12-12 00:00:00</itemsDeliveryDateEndDate>\n'
            b'        </item>\n'
            b'        <item>\n'
            b'            <itemsId>222</itemsId>\n'
            b'            <itemsDescription>bla bla</itemsDescription>\n'
            b'            <itemsClassificationScheme></itemsClassificationScheme>\n'
            b'            <itemsClassificationId>678</itemsClassificationId>\n'
            b'            <itemsClassificationDescription>Banana</itemsClassificationDescription>\n'
            b'            <itemsAdditionalClassifications>\n'
            b'            </itemsAdditionalClassifications>\n'
            b'            <itemsQuantity>3</itemsQuantity>\n'
            b'            <itemsUnitName>FFA</itemsUnitName>\n'
            b'            <itemsDeliveryAddress>Kharkiv, Nauki, 23</itemsDeliveryAddress>\n'
            b'            <itemsDeliveryDateEndDate>1999-12-22 00:00:00</itemsDeliveryDateEndDate>\n'
            b'        </item></items>\n'
            b'    <milestones>\n'
            b'        <milestone>\n'
            b'            <milestonesId>122</milestonesId>\n'
            b'            <milestonesTitle>122 title</milestonesTitle>\n'
            b'            <milestonesDescription>122 description</milestonesDescription>\n'
            b'            <milestonesCode>122 code</milestonesCode>\n'
            b'            <milestonesDurationDays>12</milestonesDurationDays>\n'
            b'            <milestonesDurationType>business</milestonesDurationType>\n'
            b'            <milestonesPercentage>30</milestonesPercentage>\n'
            b'        </milestone>\n'
            b'        <milestone>\n'
            b'            <milestonesId>222</milestonesId>\n'
            b'            <milestonesTitle>222 title</milestonesTitle>\n'
            b'            <milestonesDescription>222 description</milestonesDescription>\n'
            b'            <milestonesCode>222 code</milestonesCode>\n'
            b'            <milestonesDurationDays>22</milestonesDurationDays>\n'
            b'            <milestonesDurationType>sunny</milestonesDurationType>\n'
            b'            <milestonesPercentage>70</milestonesPercentage>\n'
            b'        </milestone></milestones>\n'
            b'    <startDate>2012-04-01 00:00:00</startDate>\n'
            b'    <bids>\n'
            b'        <bid>\n'
            b'            <bidsId>1</bidsId>\n'
            b'            <bidsSuppliersIdentifierName>My name</bidsSuppliersIdentifierName>\n'
            b'            <bidsValueAmount>333</bidsValueAmount>\n'
            b'            <bidsValueAmountLast>123</bidsValueAmountLast>\n'
            b'            <awardQualifiedEligible>True</awardQualifiedEligible>\n'
            b'        </bid>\n'
            b'        <bid>\n'
            b'            <bidsId>2</bidsId>\n'
            b'            <bidsSuppliersIdentifierName>his name</bidsSuppliersIdentifierName>\n'
            b'            <bidsValueAmount>555</bidsValueAmount>\n'
            b'            <bidsValueAmountLast>321</bidsValueAmountLast>\n'
            b'            <awardQualifiedEligible>False</awardQualifiedEligible>\n'
            b'        </bid></bids>\n'
            b'    <awardComplaintPeriodStartDate>2012-04-01 00:00:00</awardComplaintPeriodStartDate>\n'
            b'    <cancellationsReason></cancellationsReason>\n'
            b'    <contractsDateSigned>2001-12-03 00:00:00</contractsDateSigned>\n'
            b'    <contractsSuppliersIdentifierName>his name</contractsSuppliersIdentifierName>\n'
            b'    <contractsSuppliersAddress>Street, 1, Kyiv</contractsSuppliersAddress>\n'
            b'    <bidSubcontractingDetails></bidSubcontractingDetails>\n'
            b'    <ContractsValueAmount>12</ContractsValueAmount>\n'
            b'    <startDateCfaua></startDateCfaua>\n'
            b'    <ContractsContractID>123</ContractsContractID>\n'
            b'</report>\n'
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
        context["contract"]["changes"] = []
        context["plan"]["additionalClassifications"] = []
        context["plan"]["budget"]["breakdown"] = []
        context["tender"]["items"] = []
        context["tender"]["milestones"] = []
        context["tender"]["bids"] = []
        result = render_contract_xml(context)
        self.assertEqual(
            result,
            b'<?xml version="1.0" encoding="windows-1251"?>\n'
            b'<root method_name="PrContract">\n'
            b'    <contract>\n'
            b'        <contractId>123</contractId>\n'
            b'        <contractNumber></contractNumber>\n'
            b'        <contractsPeriodStartDate>2001-12-01 00:00:00</contractsPeriodStartDate>\n'
            b'        <contractsPeriodEndDate>2021-12-31 00:00:00</contractsPeriodEndDate>\n'
            b'        <contractsValueAmount>12</contractsValueAmount>\n'
            b'        <contractsValueCurrency>slaves</contractsValueCurrency>\n'
            b'        <contractsValueAmountNet>13</contractsValueAmountNet>\n'
            b'        <contractsDateSigned>2001-12-03 00:00:00</contractsDateSigned>\n'
            b'        <contractsDocuments>spam=</contractsDocuments>\n'
            b'    </contract>\n'
            b'    <changes></changes>\n'
            b'    <plan>\n'
            b'    <planId>999</planId>\n'
            b'    <procuringEntityName>My name</procuringEntityName>\n'
            b'    <procuringEntityIdentifierId>99999-99</procuringEntityIdentifierId>\n'
            b'    <classificationId>678</classificationId>\n'
            b'    <classificationDescription>Banana</classificationDescription>\n'
            b'    <additionalClassifications></additionalClassifications>\n'
            b'    <budgetDescription>Budget</budgetDescription>\n'
            b'    <budgetAmount>500</budgetAmount>\n'
            b'    <budgetCurrency>UAU</budgetCurrency>\n'
            b'    <budgetAmountNet>550</budgetAmountNet>\n'
            b'    <tenderPeriodStartDate>1990-01-01 12:30:00</tenderPeriodStartDate>\n'
            b'    <tenderProcurementMethodType>belowAbove</tenderProcurementMethodType>\n'
            b'    <breakdowns></breakdowns>\n'
            b'</plan>\n'
            b'<report>\n'
            b'    <tenderID>55555</tenderID>\n'
            b'    <date>2006-05-07 00:00:00</date>\n'
            b'    <procuringEntityName>My name</procuringEntityName>\n'
            b'    <procuringEntityIdentifierId>99999-99</procuringEntityIdentifierId>\n'
            b'    <mainProcurementCategory>good goods</mainProcurementCategory>\n'
            b'    <items></items>\n'
            b'    <milestones></milestones>\n'
            b'    <startDate>2012-04-01 00:00:00</startDate>\n'
            b'    <bids></bids>\n'
            b'    <awardComplaintPeriodStartDate>2012-04-01 00:00:00</awardComplaintPeriodStartDate>\n'
            b'    <cancellationsReason></cancellationsReason>\n'
            b'    <contractsDateSigned>2001-12-03 00:00:00</contractsDateSigned>\n'
            b'    <contractsSuppliersIdentifierName>his name</contractsSuppliersIdentifierName>\n'
            b'    <contractsSuppliersAddress>Street, 1, Kyiv</contractsSuppliersAddress>\n'
            b'    <bidSubcontractingDetails></bidSubcontractingDetails>\n'
            b'    <ContractsValueAmount>12</ContractsValueAmount>\n'
            b'    <startDateCfaua></startDateCfaua>\n'
            b'    <ContractsContractID>123</ContractsContractID>\n'
            b'</report>\n'
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
        self.assertEqual({d["id"] for d in contract["documents"]}, {"22"})
        self.assertEqual({d["id"] for d in contract["changes"][0]["documents"]}, {"11"})
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


