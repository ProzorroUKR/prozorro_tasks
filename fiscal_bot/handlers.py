from .settings import procedures
from .tasks import process_tender


def fiscal_bot_tender_handler(tender):
    if tender['procurementMethodType'] in procedures and tender["status"] == "active.qualification":
        process_tender.delay(tender_id=tender['id'])
