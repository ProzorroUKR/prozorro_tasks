import yaml
from tasks_utils.requests import get_public_api_data, download_file
from celery.utils.log import get_task_logger
from treasury.settings import RELEASE_2020_04_19


logger = get_task_logger(__name__)


def get_contract_date(task, contract):
    if "dateSigned" in contract:
        return contract["dateSigned"]
    else:
        tender = get_public_api_data(task, contract["tender_id"], "tender")
        tender_contract = [
            c for c in tender["contracts"]
            if c["id"] == contract["id"]
        ][0]
        return tender_contract["date"]


def get_first_stage_tender(task, tender):
    if tender["procurementMethodType"] in ("competitiveDialogueEU.stage2", "competitiveDialogueUA.stage2"):
        tender_id_first_stage = tender["dialogueID"]
        first_stage_tender = get_public_api_data(task, tender_id_first_stage, "tender")
    elif tender["procurementMethodType"] == "closeFrameworkAgreementSelectionUA":
        tender_id_first_stage = tender["agreements"][0]["tender_id"]
        first_stage_tender = get_public_api_data(task, tender_id_first_stage, "tender")
    else:
        # tender initially was in the first stage
        first_stage_tender = tender
    return first_stage_tender


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


def prepare_context(task, contract, tender, plan, buyer):
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
        b for b in tender.get("bids", "")
        if b["id"] == tender_award.get("bid_id")
    ]
    tender_bid = tender_bid[0] if tender_bid else {}

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
    tender["bids"] = [b for b in tender.get("bids", "") if b.get("status") not in ("deleted", "invalid",)]

    # filter lot items
    if related_lot:
        filtered_bids = []
        for b in tender["bids"]:
            for lot_value in b.get("lotValues", ""):
                if lot_value["relatedLot"] == related_lot:
                    b["value"] = lot_value["value"]
                    filtered_bids.append(b)
        tender["bids"] = filtered_bids

    def lot_related(e):
        return e.get("relatedLot") == related_lot

    tender["milestones"] = list(filter(lot_related, tender.get("milestones", "")))
    tender["items"] = list(filter(lot_related, tender["items"]))

    # getting auction info (if bids exist)

    initial_bids = {}
    if tender_bid:
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
    tender = get_award_qualified_eligible_for_each_bid(tender)

    for item in tender["items"]:
        item["item_delivery_address"] = get_custom_address_string(item.get("deliveryAddress"))

    data_organization = plan.get("procuringEntity")
    if buyer:
        data_organization = buyer

    plan["procuring_entity_name"] = get_name_from_organization(data_organization)
    plan["procuring_identifier_id"] = get_name_from_organization(data_organization)

    for bid in tender["bids"]:
        bid["bid_suppliers_identifier_name"] = get_name_from_organization(bid["tenderers"][0])

    tender_start_date = get_tender_start_date(tender, tender_award, tender_contract)

    secondary_data = dict(
        tender_start_date=tender_start_date,
        award_complaint_period_start_date=get_award_complaint_period_start_date(tender_award),
        contracts_suppliers_address=get_custom_address_string(tender_contract.get("suppliers")[0]["address"]),
        contracts_suppliers_identifier_name=get_name_from_organization(tender_contract["suppliers"][0]),
        tender_procuring_entity_name=get_name_from_organization(tender.get("procuringEntity")),
        bid_subcontracting_details=get_bid_subcontracting_details(tender_award, tender_bid, related_lot, tender),
        procuring_entity_kind=get_procuring_entity_kind(tender_start_date, tender)
    )

    context = dict(
        contract=contract,
        tender=tender,
        tender_contract=tender_contract,
        tender_bid=tender_bid,
        lot=lot,
        cancellation=cancellation,
        plan=plan,
        initial_bids=initial_bids,
        secondary_data=secondary_data,
    )
    return context


def get_tender_start_date(tender, tender_award, tender_contract):
    tender_procurement_method_type = tender["procurementMethodType"]

    if tender_procurement_method_type in (
            "belowThreshold", "aboveThresholdUA", "aboveThresholdEU", "aboveThresholdUA.defense",
            "competitiveDialogueUA.stage2", "competitiveDialogueEU.stage2", "closeFrameworkAgreementSelectionUA",
            "esco",
    ):
        return tender["enquiryPeriod"]["startDate"]
    elif tender_procurement_method_type in ("negotiation", "negotiation.quick", ):
        return tender_award["complaintPeriod"]["startDate"]

    elif tender_procurement_method_type in ("reporting", ):
        # TODO will be added esco procurementMethodType after changes to API
        return tender_contract["dateSigned"]

    elif tender_procurement_method_type in ("priceQuotation", ):
        return tender["tenderPeriod"]["startDate"]
    else:
        logger.warning(
            f"Cannot find such {tender_procurement_method_type} procurementMethodType in tender",
            extra={
                "MESSAGE_ID": "TREASURY_UNKNOWN_PROCUREMENT_METHOD_TYPE",
                "TENDER_ID": tender["id"]
            }
        )
        return None


def get_award_complaint_period_start_date(tender_award):
    return tender_award.get("date")


def get_custom_address_string(address):
    if not address:
        return None

    custom_address_order = ("postalCode", "countryName", "region", "locality", "streetAddress")
    res = []

    for field in custom_address_order:
        field_value = address.get(field)
        if field_value:
            res.append(field_value)
    return ", ".join(str(el) for el in res)


def get_award_qualified_eligible_for_each_bid(tender):
    for bid in tender['bids']:
        bid['award_qualified_eligible'] = get_award_qualified_eligible(tender, bid)
    return tender


def get_award_qualified_eligible(tender, bid):

    tender_procurement_method_type = tender["procurementMethodType"]
    if tender_procurement_method_type in (
            "aboveThresholdUA", "aboveThresholdUA.defense",
            "competitiveDialogueUA.stage2",
    ):
        _award = [
            a for a in tender["awards"]
            if a["bid_id"] == bid["id"]
        ]
        if not _award:
            return None
        _award = _award[0]

        return handle_award_qualified_eligible_statuses(_award)

    elif tender_procurement_method_type in ("aboveThresholdEU", "competitiveDialogueEU.stage2"):
        _qualification = [
            q for q in tender["qualifications"]
            if q["bidID"] == bid["id"]
        ]

        if not _qualification:
            return None
        _qualification = _qualification[-1]  # should get last qualification

        return handle_award_qualified_eligible_statuses(_qualification)

    elif tender_procurement_method_type in ("closeFrameworkAgreementSelectionUA", ):
        return True

    elif tender_procurement_method_type in (
            "belowThreshold", "reporting", "esco", "priceQuotation", "negotiation", "negotiation.quick"
    ):
        return None
    else:
        logger.warning(
            f"Cannot find {tender_procurement_method_type} procurementMethodType in tender",
            extra={
                "MESSAGE_ID": "TREASURY_UNKNOWN_PROCUREMENT_METHOD_TYPE",
                "TENDER_ID": tender["id"]
            }
        )
        return None


def handle_award_qualified_eligible_statuses(_tender_object):
    """general business logic for handling statuses of (award and qualification) _tender_object """

    if _tender_object["status"] == "active":
        return True
    elif _tender_object["status"] == "unsuccessful":
        return f"{_tender_object.get('title', '')} {_tender_object.get('description', '')}"
    elif _tender_object["status"] == "pending":
        return None
    elif _tender_object["status"] == "cancelled":
        return "Рішення скасоване"
    else:
        return None


def get_name_from_organization(_object):
    if not _object:
        return None

    if "legalName" in _object["identifier"]:
        return _object["identifier"]["legalName"]
    return _object["name"]


def get_identifier_id_from_organization(_object):
    if not _object:
        return None

    if "id" in _object["identifier"]:
        return _object["identifier"]["id"]
    return _object["name"]


def get_bid_subcontracting_details(tender_award, tender_bid, related_lot, tender):
    if 'lots' in tender:
        lot_value = [lot_val for lot_val in tender_bid.get("lotValues", "")
                     if lot_val["relatedLot"] == related_lot]
        return lot_value[0].get("subcontractingDetails") if lot_value else None
    elif tender["procurementMethodType"] in ("negotiation", "negotiation.quick", "reporting",):
        return tender_award.get("subcontractingDetails")
    else:
        return tender_bid.get("subcontractingDetails")


def get_procuring_entity_kind(tender_start_date, tender):
    if not tender_start_date or tender_start_date < RELEASE_2020_04_19:
        return None
    return tender["procuringEntity"].get("kind")
