from asgiref.sync import sync_to_async

from .settings import (
    pre_qualification_procedures,
    qualification_procedures,
    qualification_procedures_limited,
)
from .tasks import process_tender


def valid_qualification_tender(tender):
    return (
        tender.get('status') == "active.qualification" and
        tender.get('procurementMethodType') in qualification_procedures
    )


def valid_pre_qualification_tender(tender):
    return (
        tender.get('status') == 'active.pre-qualification' and
        tender.get('procurementMethodType') in pre_qualification_procedures
    )


def valid_qualification_limited_tender(tender):
    return (
        tender.get('status') == 'active' and
        tender.get('procurementMethodType') in qualification_procedures_limited
    )


async def edr_bot_tender_handler(tender, **kwargs):
    if (
        valid_qualification_tender(tender) or
        valid_pre_qualification_tender(tender) or
        valid_qualification_limited_tender(tender)
    ):
        await sync_to_async(process_tender.delay)(tender_id=tender['id'])
