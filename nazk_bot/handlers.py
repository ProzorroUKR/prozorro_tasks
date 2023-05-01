from asgiref.sync import sync_to_async

from .settings import nazk_procedures
from .tasks import process_tender


async def nazk_bot_tender_handler(tender, **_):
    if (
            tender.get('status') in ["active.qualification", "active.awarded"] and
            tender.get('procurementMethodType') in nazk_procedures
    ):
        await sync_to_async(process_tender.delay)(tender_id=tender['id'])
