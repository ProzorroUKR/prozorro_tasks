from datetime import datetime
from lxml import etree, builder


DOC_TYPE = b'<?xml version="1.0" encoding="windows-1251"?>'


def _render_tree(xml):
    result = DOC_TYPE + etree.tostring(xml, encoding="windows-1251", xml_declaration=False)
    return result


def format_date(dt):
    if isinstance(dt, datetime):
        return dt.isoformat()
    return dt


def get_value(obj, *keys, formatter=str, default=None):
    for key in keys:
        obj = obj.get(key)
        if obj is None:
            return default

    if isinstance(obj, dict):
        obj = list(obj.values())  # deliveryAddress

    if isinstance(obj, list):
        obj = ", ".join(formatter(e) for e in obj)  # ex.: rationaleTypes

    if obj == "":
        return None  # this will hide this tag

    return formatter(obj)


def get_date_value(obj, *keys, default=None):
    return get_value(obj, *keys, formatter=format_date, default=default)


class TreasuryElementMaker(builder.ElementMaker):
    """
    Elements without children return None
    and won't be passed to their parents, as None children are skipped
    ex:
        maker.ul(
            maker.li( {"1": 1}.get("1") ),
            maker.li( {"1": 1}.get("2") ),
        )
        returns
        <ul><li>1</li></ul>
    """
    def __call__(self, tag, *children, **attrib):
        children = tuple(c for c in children if c is not None)
        if children:
            return super().__call__(tag, *children, **attrib)


def render_change_xml(context):
    contract = context["contract"]
    change = context["change"]
    maker = TreasuryElementMaker()
    xml = maker.root(
        maker.contractId(contract["id"]),
        maker.contractsDateSigned(get_date_value(contract, "dateSigned")),
        maker.contractsValueAmount(get_value(contract, "value", "amount")),
        maker.contractsValueCurrency(get_value(contract, "value", "currency")),
        maker.contractsValueAmountNet(get_value(contract, "value", "amountNet")),
        maker.changeId(change["id"]),
        maker.changeContractNumber(get_value(change, "contractNumber")),
        maker.changeRationale(get_value(change, "rationale")),
        maker.changeRationaleTypes(get_value(change, "rationaleTypes")),
        maker.DateSigned(get_date_value(change, "dateSigned")),
        maker.changeDocuments(get_value(change, "documents")),
        method_name="PrChange",
    )
    return _render_tree(xml)


def _build_plan_xml(maker, context):
    plan = context.get("plan")
    if plan:
        result = maker.plan(
            maker.planId(plan["id"]),
            maker.procuringEntityName(get_value(plan, "procuring_entity_name")),
            maker.procuringEntityIdentifierId(get_value(plan, "procuringEntity", "identifier", "id")),
            maker.classificationId(get_value(plan, "classification", "id")),
            maker.classificationDescription(get_value(plan, "classification", "description")),
            maker.additionalClassifications(
                * (
                    maker.additionalClassification(
                        maker.additionalClassificationsScheme(get_value(classification, "scheme")),
                        maker.additionalClassificationsId(get_value(classification, "id")),
                        maker.additionalClassificationsDescription(get_value(classification, "description")),
                    ) for classification in plan.get("additionalClassifications", "")
                )
            ),
            maker.budgetDescription(get_value(plan, "budget", "description")),
            maker.budgetAmount(get_value(plan, "budget", "amount")),
            maker.budgetCurrency(get_value(plan, "budget", "currency")),
            maker.budgetAmountNet(get_value(plan, "budget", "amountNet")),
            maker.tenderPeriodStartDate(get_date_value(plan, "tender", "tenderPeriod", "startDate")),
            maker.tenderProcurementMethodType(get_value(plan, "tender", "procurementMethodType")),
            maker.breakdowns(
                * (
                        maker.breakdown(
                        maker.breakdownId(get_value(breakdown, "id")),
                        maker.breakdownTitle(get_value(breakdown, "title")),
                        maker.breakdownDescription(get_value(breakdown, "description")),
                        maker.breakdownAmount(get_value(breakdown, "value", "amount")),
                    ) for breakdown in plan.get("budget", {}).get("breakdown", "")
                )
            ),
        )
        return result


def _build_tender_xml(maker, context):
    tender = context["tender"]
    tender_contract = context["tender_contract"]
    tender_bid = context["tender_bid"]
    initial_bids = context["initial_bids"]
    secondary_data = context["secondary_data"]

    lot = context.get("lot")
    result = maker.report(
        maker.tenderID(tender["tenderID"]),
        maker.date(get_date_value(
            lot if lot else tender,
            "date"
        )),
        maker.procuringEntityName(secondary_data["tender_procuring_entity_name"]),
        maker.procuringEntityIdentifierId(get_value(tender, "procuringEntity", "identifier", "id")),
        maker.mainProcurementCategory(get_value(tender, "mainProcurementCategory")),
        maker.items(
            * (maker.item(
                maker.itemsId(item["id"]),
                maker.itemsDescription(get_value(item, "description")),
                maker.itemsClassificationScheme(get_value(item, "classification", "scheme")),
                maker.itemsClassificationId(get_value(item, "classification", "id")),
                maker.itemsClassificationDescription(get_value(item, "classification", "description")),
                maker.itemsAdditionalClassifications(
                    *(maker.itemsAdditionalClassification(
                        maker.itemsAdditionalClassificationsScheme(get_value(classification, "scheme")),
                        maker.itemsAdditionalClassificationsId(get_value(classification, "id")),
                        maker.itemsAdditionalClassificationsDescription(get_value(classification, "description")),
                    ) for classification in item.get("additionalClassifications", ""))
                ),
                maker.itemsQuantity(get_value(item, "quantity")),
                maker.itemsUnitName(get_value(item, "unit", "name")),
                maker.itemsDeliveryAddress(get_value(item, "item_delivery_address")),
                maker.itemsDeliveryDateEndDate(get_date_value(item, "deliveryDate", "endDate")),
            ) for item in tender['items'])
        ),
        maker.milestones(
            * (maker.milestone(
                maker.milestonesId(milestone["id"]),
                maker.milestonesTitle(get_value(milestone, "title")),
                maker.milestonesDescription(get_value(milestone, "description")),
                maker.milestonesCode(get_value(milestone, "code")),
                maker.milestonesDurationDays(get_value(milestone, "duration", "days")),
                maker.milestonesDurationType(get_value(milestone, "duration", "type")),
                maker.milestonesPercentage(get_value(milestone, "percentage")),
            ) for milestone in tender.get("milestones", ""))
        ),
        maker.startDate(format_date(secondary_data["tender_start_date"])),
        maker.bids(* (
            maker.bid(
                maker.bidsId(bid["id"]),
                maker.bidsSuppliersIdentifierName(get_value(bid, "bid_suppliers_identifier_name")),
                maker.bidsValueAmount(get_value(initial_bids, bid["id"])),
                maker.bidsValueAmountLast(get_value(bid, "value", "amount")),
                maker.awardQualifiedEligible(get_value(bid, "award_qualified_eligible")),
            ) for bid in tender["bids"]  # can be empty bids list here
        )),
        maker.awardComplaintPeriodStartDate(
            format_date(secondary_data["award_complaint_period_start_date"])
        ),
        maker.contractsDateSigned(get_date_value(tender_contract, "dateSigned")),
        maker.contractsSuppliersIdentifierName(
            secondary_data["contracts_suppliers_identifier_name"]
        ),
        maker.contractsSuppliersAddress(
            secondary_data["contracts_suppliers_address"]
        ),
        maker.bidSubcontractingDetails(get_value(tender_bid, "subcontractingDetails")),
        maker.ContractsValueAmount(get_value(tender_contract, "value", "amount")),
        maker.startDateCfaua(None),  # will be added later
        maker.ContractsContractID(tender_contract["id"]),  # will be added later
        maker.lotsTitle(get_value(lot, "title") if lot else None)
    )
    return result


def render_contract_xml(context):
    contract = context["contract"]
    maker = TreasuryElementMaker()
    parts = [
        maker.contract(
            maker.contractId(contract["id"]),
            maker.contractNumber(get_value(contract, "contractNumber")),
            maker.contractsPeriodStartDate(get_date_value(contract, "period", "startDate")),
            maker.contractsPeriodEndDate(get_date_value(contract, "period", "endDate")),
            maker.contractsValueAmount(get_value(contract, "value", "amount")),
            maker.contractsValueCurrency(get_value(contract, "value", "currency")),
            maker.contractsValueAmountNet(get_value(contract, "value", "amountNet")),
            maker.contractsDateSigned(get_date_value(contract, "dateSigned")),
            maker.contractsDocuments(get_value(contract, "documents")),
        ),
        maker.changes(
            * (maker.change(
                maker.changeId(change["id"]),
                maker.contractNumber(change["contractNumber"]),
                maker.changeRationale(get_value(change, "rationale")),
                maker.changeRationaleTypes(get_value(change, "rationaleTypes")),
                maker.contractsDateSigned(get_date_value(change, "dateSigned")),
                maker.changeDocuments(get_value(change, "documents")),
            ) for change in contract.get("changes", ""))
        ),
    ]
    plan = _build_plan_xml(maker, context)
    if plan is not None:
        parts.append(plan)
    parts.append(
        _build_tender_xml(maker, context)
    )
    xml = maker.root(
        *parts,
        method_name="PrContract",
    )
    return _render_tree(xml)


def render_catalog_xml(context):
    maker = TreasuryElementMaker()
    xml = maker.root(
        maker.ref(
            "",
            id=get_value(context, "catalog_id"),
            date=get_date_value(context, "since_date", default="")
        ),
        method_name="GetRef"
    )
    return _render_tree(xml)


def render_transactions_confirmation_xml(register_id, status_id, date, rec_count, reg_sum):
    maker = builder.ElementMaker()
    xml = maker.root(
        maker.register_id(str(register_id)),
        maker.status_id(str(status_id)),
        maker.date(date),
        maker.rec_count(str(rec_count)),
        maker.reg_sum(str(reg_sum)),
        method_name="ConfirmPRTrans",
    )
    return _render_tree(xml)
