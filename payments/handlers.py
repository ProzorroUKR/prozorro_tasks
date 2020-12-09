from payments.settings import non_complaint_procedures
from payments.tasks import process_tender
from tasks_utils.datetime import parse_dt_string, get_now
from environment_settings import PAYMENTS_SKIP_TENDER_DAYS
from datetime import timedelta


def payments_tender_handler(tender, **kwargs):
    delta = get_now() - parse_dt_string(tender['dateModified'])
    if tender['procurementMethodType'] not in non_complaint_procedures:
        if delta < timedelta(days=PAYMENTS_SKIP_TENDER_DAYS):
            process_tender.delay(tender_id=tender['id'])
