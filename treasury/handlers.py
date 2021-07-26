from asgiref.sync import sync_to_async

from environment_settings import TREASURY_INT_START_DATE
from .tasks import check_contract


async def contract_handler(contract, **kwargs):  # only "id" and "contractID" can be received from feed
    # TODO: add status to feed and filter contracts not in active status
    if contract["dateModified"] >= TREASURY_INT_START_DATE:
        await sync_to_async(check_contract.delay)(contract_id=contract['id'])
