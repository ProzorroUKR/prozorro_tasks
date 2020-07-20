import requests
from tasks_utils.settings import CONNECT_TIMEOUT, READ_TIMEOUT, RETRY_REQUESTS_EXCEPTIONS
from treasury.exceptions import DocumentServiceForbiddenError, DocumentServiceError, ApiServiceError
from environment_settings import (
    API_VERSION, DS_HOST, DS_USER, DS_PASSWORD,
)
from environment_settings import API_HOST, API_VERSION, API_TOKEN
from app.logging import getLogger
from treasury.settings import (
    PUT_TRANSACTION_SUCCESSFUL_STATUS,
    ATTACH_DOCUMENT_TO_TRANSACTION_SUCCESSFUL_STATUS,
)

logger = getLogger()


def save_transaction_xml(transactions_ids, source):
    if len(transactions_ids) > 1:
        file_name = f"Transaction_{transactions_ids[0]}_and_{len(transactions_ids)-1}_others.xml"
    else:
        file_name = f"Transaction_{transactions_ids[0]}.xml"
    document = ds_upload(
        file_name=file_name,
        file_content=source
    )
    return document


def ds_upload(file_name, file_content):
    try:
        response = requests.post(
            '{host}/upload'.format(host=DS_HOST),
            auth=(DS_USER, DS_PASSWORD),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            files={'file': (file_name, file_content)},
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        raise DocumentServiceError(description=f'Connection Error to Document Service {DS_HOST} host, {exc}')
    else:
        if response.status_code == 403:
            raise DocumentServiceForbiddenError(description=f'Forbidden 403, {DS_HOST}/upload not allowed')
        elif response.status_code != 200:
            raise DocumentServiceError(
                description=f'Status code: {response.status_code}. Incorrect upload status for doc {file_name}'
            )
        else:
            logger.info(
                f"{file_name} was successfully saved to Document Service"
            )
            return response.json()


def put_transaction(transaction):
    contract_id = transaction["id_contract"]
    transaction_id = transaction["ref"]

    data = dict(
        date=transaction["msrprd_date"],
        value=dict(
            amount=transaction["doc_sq"],
            currency="UAH"
        ),
        payer=dict(
            id=transaction["doc_iban_a"],
            name=transaction["doc_nam_a"],
        ),
        payee=dict(
            id=transaction["doc_iban_b"],
            name=transaction["doc_nam_b"],
        ),
        status=transaction["doc_status"]
    )

    timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)

    session = requests.Session()
    url = f"{API_HOST}/api/{API_VERSION}/contracts/{contract_id}/transactions/{transaction_id}"
    log_context = {
        "CONTRACT_ID": contract_id,
        "TRANSACTION_ID": transaction_id,
    }
    try:
        get_response = session.get(f"{API_HOST}/api/{API_VERSION}/contracts/{contract_id}")
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        raise ApiServiceError(description=f'Connection Error to Api Service {API_HOST} host, {exc}')
    if get_response.status_code != 200:
        logger.error(
            f"Can not find {contract_id} contract id",
            extra={
                "MESSAGE_ID": "TREASURY_TRANS_PRECONDITION_ERROR",
                "RESPONSE_TEXT": get_response.text, **log_context
            }
        )
        return get_response.status_code
    response = session.put(
        url, json={'data': data}, timeout=timeout,
        headers={'Authorization': 'Bearer {}'.format(API_TOKEN)},
    )

    log_context["RESPONSE_STATUS"] = response.status_code

    if response.status_code == 422:
        logger.error(
            "Incorrect transaction data, Unprocessable Entity",
            extra={
                "MESSAGE_ID": "TREASURY_TRANS_ERROR",
                "RESPONSE_TEXT": response.text, **log_context
            }
        )
        return response.status_code
    elif response.status_code not in (201, 200):
        logger.error(
            "Unexpected status",
            extra={
                "MESSAGE_ID": "TREASURY_TRANS_UNSUCCESSFUL_STATUS",
                "RESPONSE_TEXT": response.text, **log_context
            })
        return response.status_code
    else:
        logger.info(
            "Transaction successfully saved",
            extra={"MESSAGE_ID": "TREASURY_TRANS_SUCCESSFUL", **log_context}
        )
        return PUT_TRANSACTION_SUCCESSFUL_STATUS


def attach_doc_to_contract(data, contract_id, transaction_id):

    url = "{host}/api/{version}/contracts/{contract_id}/transactions/{transaction_id}/documents".format(
        host=API_HOST,
        version=API_VERSION,
        contract_id=contract_id,
        transaction_id=transaction_id
    )

    timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)

    get_url = "{host}/api/{version}/contracts/{contract_id}/transactions/{transaction_id}".format(
        host=API_HOST,
        version=API_VERSION,
        contract_id=contract_id,
        transaction_id=transaction_id
    )

    session = requests.Session()
    try:
        get_response = session.get(
            get_url,
            headers={
                'Authorization': 'Bearer {}'.format(API_TOKEN),
            },
            timeout=timeout
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        raise ApiServiceError(description=f'Connection Error to Api Service {API_HOST} host, {exc}')

    if get_response.status_code != 200:
        logger.error(
            f"Can not find {transaction_id} transaction id during attaching document to contract",
            extra={
                "MESSAGE_ID": "TREASURY_TRANS_PRECONDITION_ERROR",
                "RESPONSE_TEXT": get_response.text
            }
        )
        return get_response.status_code
    else:
        response = session.post(
            url,
            json={'data': data},
            headers={
                'Authorization': 'Bearer {}'.format(API_TOKEN),
            },
            timeout=timeout,
            cookies=get_response.cookies
        )
        # handle response code
        if response.status_code == 422:
            logger.error("Incorrect document data while attaching doc {} to transaction {}: {}".format(
                data["title"], transaction_id, response.text
            ), extra={"MESSAGE_ID": "ATTACH_DOC_DATA_ERROR"})
            return response.status_code
        elif response.status_code == 403:
            logger.warning(
                "Forbidden, Can't upload document: {}".format(response.text),
                extra={"MESSAGE_ID": "ATTACH_DOC_UNSUCCESSFUL_STATUS", "STATUS_CODE": response.status_code}
            )
            return response.status_code
        elif response.status_code != 201:
            logger.error("Incorrect upload status while attaching doc {} to transaction {}: {}".format(
                data["title"], transaction_id, response.text
            ), extra={"MESSAGE_ID": "ATTACH_DOC_UNSUCCESSFUL_STATUS", "STATUS_CODE": response.status_code})
            return response.status_code
        else:
            logger.info(
                "File {} was successful attached to {} transaction".format(data["title"], transaction_id),
                extra={"MESSAGE_ID": "SUCCESSFUL_DOC_ATTACHED"}
            )
            return ATTACH_DOCUMENT_TO_TRANSACTION_SUCCESSFUL_STATUS
