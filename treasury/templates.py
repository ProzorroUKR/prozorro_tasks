from tasks_utils.requests import download_file
from environment_settings import TREASURY_DATETIME_FMT
from environment_settings import TIMEZONE
from datetime import datetime
from lxml import etree, builder
import dateutil.parser
import yaml


DOC_TYPE = b'<?xml version="1.0" encoding="windows-1251"?>'


def _render_tree(xml):
    result = DOC_TYPE + etree.tostring(xml, encoding="windows-1251", xml_declaration=False)
    return result


def format_date(dt):
    if dt:
        if not isinstance(dt, datetime):
            dt = dateutil.parser.parse(dt).astimezone(TIMEZONE)
        return dt.strftime(TREASURY_DATETIME_FMT)


def get_value(obj, *keys, formatter=str, default=None):
    for key in keys:
        obj = obj.get(key)
        if obj is None:
            return default

    if isinstance(obj, dict):
        obj = list(obj.values())  # deliveryAddress

    if isinstance(obj, list):
        return ", ".join(formatter(e) for e in obj)  # ex.: rationaleTypes

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
            maker.procuringEntityName(get_value(plan, "procuringEntity", "name")),
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
    tender_award = context["tender_award"]
    tender_contract = context["tender_contract"]
    tender_bid = context["tender_bid"]
    initial_bids = context["initial_bids"]
    lot = context.get("lot")
    result = maker.report(
        maker.tenderID(tender["tenderID"]),
        maker.date(get_date_value(
            lot if lot else tender,
            "date"
        )),
        maker.procuringEntityName(get_value(tender, "procuringEntity", "name")),
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
                maker.itemsDeliveryAddress(get_value(item, "deliveryAddress")),
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
        maker.startDate(get_date_value(tender_award, "complaintPeriod", "startDate")),
        maker.bids(* (
            maker.bid(
                maker.bidsId(bid["id"]),
                maker.bidsSuppliersIdentifierName(get_value(bid.get("tenderers")[0], "identifier", "legalName")),
                maker.bidsValueAmount(get_value(initial_bids, bid["id"])),
                maker.bidsValueAmountLast(get_value(bid, "value", "amount")),
                maker.awardQualifiedEligible(get_value(bid, "selfQualified")),
            ) for bid in tender["bids"]
        )),
        maker.awardComplaintPeriodStartDate(get_date_value(tender_award, "complaintPeriod", "startDate")),
        maker.contractsDateSigned(get_date_value(tender_contract, "dateSigned")),
        maker.contractsSuppliersIdentifierName(
            get_value(tender_contract.get("suppliers")[0], "identifier", "legalName")
        ),
        maker.contractsSuppliersAddress(get_value(tender_contract.get("suppliers")[0], "address")),
        maker.bidSubcontractingDetails(get_value(tender_bid, "subcontractingDetails")),
        maker.ContractsValueAmount(get_value(tender_contract, "value", "amount")),
        maker.startDateCfaua(None),  # will be added later
        maker.ContractsContractID(tender_contract["id"]),  # will be added later
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
            ) for change in contract.get("changes"))
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


def prepare_contract_context(contract):
    contract["documents"] = []  # TODO:  sending documents are disabled, since UnityBars cannot process them
    # split documents
    changes = {c["id"]: c for c in contract.get("changes", "")}
    filtered_documents = []
    for doc in contract.get("documents", ""):
        if doc["documentOf"] == "change":
            change = changes[doc["relatedItem"]]
            change["documents"] = change.get("documents", [])
            change["documents"].append(doc)
        else:
            filtered_documents.append(doc)
    contract["documents"] = filtered_documents


def prepare_context(task, contract, tender, plan):
    prepare_contract_context(contract)
    # additional global context variables
    tender_contract = [
        c for c in tender["contracts"]
        if c["id"] == contract["id"]
    ][0]
    tender_award = [
        a for a in tender["awards"]
        if a["id"] == contract["awardID"]
    ][0]
    tender_bid = [
        b for b in tender["bids"]
        if b["id"] == tender_award["bid_id"]
    ][0]
    related_lot = tender_award.get("lotID")
    lot = [
        l for l in tender.get("lots", "")
        if l["id"] == related_lot
    ]
    lot = lot[0] if lot else None
    cancellation = [
        c for c in tender.get("cancellations", "")
        if c["status"] == "active" and c.get("relatedLot") == related_lot
    ]
    cancellation = cancellation[0] if cancellation else {}
    tender["bids"] = [b for b in tender["bids"] if b.get("status") != "deleted"]

    # filter lot items
    if related_lot:
        filtered_bids = []
        for b in tender["bids"]:
            for lot_value in b["lotValues"]:
                if lot_value["relatedLot"] == related_lot:
                    b["value"] = lot_value["value"]
                    filtered_bids.append(b)
        tender["bids"] = filtered_bids

    def lot_related(e):
        return e.get("relatedLot") == related_lot

    tender["milestones"] = list(filter(lot_related, tender.get("milestones", "")))
    tender["items"] = list(filter(lot_related, tender["items"]))

    # getting auction info
    lot_suffix = f"_{related_lot}" if related_lot else ""
    audit_doc_title = f"audit_{tender['id']}{lot_suffix}.yaml"
    for doc in tender.get("documents", ""):
        if doc["title"] == audit_doc_title:
            _, content = download_file(task, doc["url"])
            auction_info = yaml.safe_load(content)
            initial_bids = {
                str(b["bidder"]): b["amount"]
                for b in auction_info["timeline"]["auction_start"]["initial_bids"]
            }
            break
    else:
        initial_bids = {}

    context = dict(
        contract=contract,
        tender=tender,
        tender_award=tender_award,
        tender_contract=tender_contract,
        tender_bid=tender_bid,
        lot=lot,
        cancellation=cancellation,
        plan=plan,
        initial_bids=initial_bids,
    )
    return context
