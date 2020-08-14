import yaml
from tasks_utils.requests import get_public_api_data, download_file


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
    tender["bids"] = [b for b in tender.get("bids", "") if b.get("status") != "deleted"]

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

    tender_start_date = get_tender_start_date(tender, tender_award, tender_contract)
    award_complaint_period_start_date = get_award_complaint_period_start_date(tender, tender_award)

    context = dict(
        contract=contract,
        tender=tender,
        tender_contract=tender_contract,
        tender_bid=tender_bid,
        lot=lot,
        cancellation=cancellation,
        plan=plan,
        initial_bids=initial_bids,
        tender_start_date=tender_start_date,
        award_complaint_period_start_date=award_complaint_period_start_date,
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
        return None


def get_award_complaint_period_start_date(tender, tender_award):
    tender_procurement_method_type = tender["procurementMethodType"]

    if tender_procurement_method_type in ("closeFrameworkAgreementSelectionUA", "reporting"):
        award_start_date = tender_award["date"]
    else:
        award_start_date = tender_award["complaintPeriod"]["startDate"]
    return award_start_date
