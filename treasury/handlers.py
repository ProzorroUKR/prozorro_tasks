from environment_settings import TREASURY_INT_START_DATE
from .tasks import check_contract


def contract_handler(contract):  # only "id" and "contractID" can be received from feed
    # TODO: add status to feed and filter contracts not in active status
    if contract["dateModified"] >= TREASURY_INT_START_DATE:
        check_contract.delay(contract_id=contract['id'])
