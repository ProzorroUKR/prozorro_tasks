from .tasks import check_contract


def contract_handler(contract):  # only "id" and "contractID" can be received from feed
    if contract['status'] == 'active':
        check_contract.delay(contract_id=contract['id'])
