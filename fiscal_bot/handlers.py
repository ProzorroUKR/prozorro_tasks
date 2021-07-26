from asgiref.sync import sync_to_async
from .settings import fiscal_procedures, fiscal_statuses
from .tasks import process_tender


async def fiscal_bot_tender_handler(tender, **kwargs):
    if (
        tender.get('procurementMethodType') in fiscal_procedures and
        tender.get("status") in fiscal_statuses
    ):
        await sync_to_async(process_tender.delay)(tender_id=tender['id'])
