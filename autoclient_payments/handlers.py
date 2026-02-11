from asgiref.sync import sync_to_async

from autoclient_payments.settings import non_complaint_procedures
from autoclient_payments.tasks import process_tender
from tasks_utils.datetime import parse_dt_string, get_now
from environment_settings import PAYMENTS_SKIP_TENDER_DAYS
from datetime import timedelta


async def autoclient_payments_tender_handler(tender, **kwargs):
    delta = get_now() - parse_dt_string(tender["dateModified"])
    if (
        delta < timedelta(days=PAYMENTS_SKIP_TENDER_DAYS)
        and tender.get("procurementMethodType") not in non_complaint_procedures
    ):
        await sync_to_async(process_tender.delay)(tender_id=tender["id"])
