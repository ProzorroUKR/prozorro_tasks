from .settings import pre_qualification_procedures, qualification_procedures
from .tasks import process_tender


def valid_qualification_tender(tender):
    return (tender['status'] == "active.qualification" and
            tender['procurementMethodType'] in qualification_procedures)


def valid_pre_qualification_tender(tender):
    return (tender['status'] == 'active.pre-qualification' and
            tender['procurementMethodType'] in pre_qualification_procedures)


def edr_bot_tender_handler(tender):
    if valid_qualification_tender(tender) or valid_pre_qualification_tender(tender):
        process_tender.delay(tender_id=tender['id'], tender_status=tender['status'])
