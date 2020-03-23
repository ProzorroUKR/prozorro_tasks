from tasks_utils.requests import download_file
from environment_settings import TREASURY_DATETIME_FMT
from environment_settings import TIMEZONE
from datetime import datetime, time, timedelta
import dateutil.parser
import jinja2
import yaml


TEMPLATES = jinja2.Environment(
    loader=jinja2.PackageLoader('treasury', 'templates', encoding='windows-1251'),
)


def render_change_xml(context):
    return _render_xml("change", context)


def render_contract_xml(context):
    return _render_xml("contract", context)


def render_catalog_xml(context):
    return _render_xml("catalog", context)


def _render_xml(name, context):
    context["format_date"] = format_date
    template = TEMPLATES.get_template(f'{name}.xml')
    try:
        content = template.render(context)
    except Exception as e:  # pragma: no cover
        tb = e.__traceback__  # problems with rendering exceptions due utf-8 encoding issues of windows-1251
        while tb.tb_next:
            print(tb.tb_frame)
            tb = tb.tb_next
        print(e)
        raise
    return content.encode('windows-1251', errors='ignore')


def format_date(dt):
    if dt:
        if not isinstance(dt, datetime):
            dt = dateutil.parser.parse(dt).astimezone(TIMEZONE)
        return dt.strftime(TREASURY_DATETIME_FMT)
    return ""


def prepare_contract_context(contract):
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

    tender["milestones"] = list(filter(lot_related, tender["milestones"]))
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
