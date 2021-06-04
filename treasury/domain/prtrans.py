import requests
from tasks_utils.settings import RETRY_REQUESTS_EXCEPTIONS, DEFAULT_HEADERS
from tasks_utils.requests import mount_retries_for_request, get_exponential_request_retry_countdown
from treasury.exceptions import DocumentServiceForbiddenError, DocumentServiceError, ApiServiceError
from environment_settings import (
    API_VERSION, DS_HOST, DS_USER, DS_PASSWORD, CONNECT_TIMEOUT, READ_TIMEOUT,
)
from environment_settings import API_HOST, API_VERSION, API_TOKEN
from app.logging import getLogger
from treasury.settings import (
    PUT_TRANSACTION_SUCCESSFUL_STATUS,
    ATTACH_DOCUMENT_TO_TRANSACTION_SUCCESSFUL_STATUS,
    PUT_TRANSACTION_FAILED_REQUESTS_EXCEPTIONS,
    DOCUMENT_ATTACH_FAILED_REQUESTS_EXCEPTIONS,
)

logger = getLogger()


def save_transaction_xml(task, transactions_ids, source):
    if len(transactions_ids) > 1:
        file_name = f"Transaction_{transactions_ids[0]}_and_{len(transactions_ids)-1}_others.xml"
    else:
        file_name = f"Transaction_{transactions_ids[0]}.xml"
    document = ds_upload(
        task,
        file_name=file_name,
        file_content=source
    )
    return document


def ds_upload(task, file_name, file_content):
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    mount_retries_for_request(session, status_forcelist=(408, 409, 412, 429, 500, 502, 503, 504))

    try:
        response = session.post(
            '{host}/upload'.format(host=DS_HOST),
            auth=(DS_USER, DS_PASSWORD),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            files={'file': (file_name, file_content)},
            headers=DEFAULT_HEADERS,
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.error(exc, extra={"MESSAGE_ID": "DOCUMENT_SERVICE_REQUEST_ERROR"})
        raise task.retry(exc=exc)
    else:
        if response.status_code != 200:
            logger.error(
                "Invalid status while uploading treasury document to DS",
                extra={
                    "MESSAGE_ID": "TREASURY_DOCUMENT_SERVICE_UNSUCCESSFUL_STATUS",
                    "STATUS_CODE": response.status_code,
                    "RESPONSE_TEXT": response.text,
                    "FILE_NAME": file_name
                }
            )
            raise task.retry(countdown=get_exponential_request_retry_countdown(task, response))
        else:
            logger.info(
                f"{file_name} was successfully saved to Document Service"
            )
            return response.json()


def get_contracts_server_id_cookies():
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    mount_retries_for_request(session, status_forcelist=(404, 408, 409, 412, 429, 500, 502, 503, 504))

    try:
        get_response = session.head(
            f"{API_HOST}/api/{API_VERSION}/contracts",
            headers=DEFAULT_HEADERS,
        )
        server_id = get_response.cookies.get("SERVER_ID", None)
        return {"SERVER_ID": server_id}

    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "TREASURY_GET_CONTRACTS_REQUESTS_EXCEPTIONS"})
        return {"SERVER_ID": None}


def put_transaction(transaction, server_id_cookie):
    contract_id = transaction["id_contract"]
    transaction_id = transaction["ref"]

    data = dict(
        date=transaction["msrprd_date"],
        value=dict(
            amount=transaction["doc_sq"],
            currency="UAH"
        ),
        payer=dict(
            bankAccount=dict(
                id=transaction["doc_iban_a"],
                scheme="IBAN",
            ),
            name=transaction["doc_nam_a"],
        ),
        payee=dict(
            bankAccount=dict(
                id=transaction["doc_iban_b"],
                scheme="IBAN",
            ),
            name=transaction["doc_nam_b"],
        ),
        status=transaction["doc_status"]
    )

    timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)

    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    mount_retries_for_request(session, status_forcelist=(404, 408, 409, 412, 429, 500, 502, 503, 504))

    url = f"{API_HOST}/api/{API_VERSION}/contracts/{contract_id}/transactions/{transaction_id}"
    log_context = {
        "CONTRACT_ID": contract_id,
        "TRANSACTION_ID": transaction_id,
    }
    try:
        get_response = session.get(
            f"{API_HOST}/api/{API_VERSION}/contracts/{contract_id}",
            headers=DEFAULT_HEADERS,
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "TREASURY_GET_CONTRACT_REQUESTS_EXCEPTIONS"})
        return PUT_TRANSACTION_FAILED_REQUESTS_EXCEPTIONS

    if get_response.status_code != 200:
        logger.error(
            "Can not find contract in API for treasury",
            extra={
                "MESSAGE_ID": "TREASURY_TRANS_PRECONDITION_ERROR",
                "STATUS_CODE": get_response.status_code,
                "RESPONSE_TEXT": get_response.text,
                **log_context
            }
        )
        return get_response.status_code

    logger.info(
        f"Cookies before put transaction: {server_id_cookie}",
        extra={"MESSAGE_ID": "TREASURY_TRANSACTION_COOKIES"}
    )

    try:
        response = session.put(
            url, json={'data': data}, timeout=timeout,
            headers={
                'Authorization': 'Bearer {}'.format(API_TOKEN),
                **DEFAULT_HEADERS,
            },
            cookies=server_id_cookie
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "TREASURY_PUT_TRANSACTION_REQUESTS_EXCEPTIONS"})
        return PUT_TRANSACTION_FAILED_REQUESTS_EXCEPTIONS

    log_context["RESPONSE_STATUS"] = response.status_code

    if response.status_code not in (201, 200):
        logger.error(
            "Unexpected status status while creating transaction for contract",
            extra={
                "MESSAGE_ID": "TREASURY_TRANS_UNSUCCESSFUL_STATUS",
                "STATUS_CODE": response.status_code,
                "RESPONSE_TEXT": response.text,
                **log_context
            }
        )
        return response.status_code
    else:
        logger.info(
            "Transaction successfully saved",
            extra={"MESSAGE_ID": "TREASURY_TRANS_SUCCESSFUL", **log_context}
        )
        return PUT_TRANSACTION_SUCCESSFUL_STATUS


def attach_doc_to_transaction(data, contract_id, transaction_id, server_id_cookie):

    post_url = "{host}/api/{version}/contracts/{contract_id}/transactions/{transaction_id}/documents".format(
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
    session.headers.update(DEFAULT_HEADERS)
    mount_retries_for_request(session, status_forcelist=(404, 408, 409, 412, 429, 500, 502, 503, 504))

    try:
        get_response = session.get(
            get_url,
            headers={
                'Authorization': 'Bearer {}'.format(API_TOKEN),
                **DEFAULT_HEADERS,
            },
            timeout=timeout,
            cookies=server_id_cookie
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "TREASURY_GET_TRANSACTION_REQUESTS_EXCEPTIONS"})
        return DOCUMENT_ATTACH_FAILED_REQUESTS_EXCEPTIONS

    if get_response.status_code != 200:
        logger.error(
            f"Can not find {transaction_id} transaction id during attaching document to contract",
            extra={
                "MESSAGE_ID": "TREASURY_TRANS_PRECONDITION_ERROR",
                "STATUS_CODE": get_response.status_code,
                "RESPONSE_TEXT": get_response.text
            }
        )
        return get_response.status_code

    logger.info(
        f"Cookies before attach doc to transaction: {server_id_cookie}",
        extra={"MESSAGE_ID": "TREASURY_TRANSACTION_COOKIES"}
    )

    try:
        response = session.post(
            post_url,
            json={'data': data},
            headers={
                'Authorization': 'Bearer {}'.format(API_TOKEN),
                **DEFAULT_HEADERS,
            },
            timeout=timeout,
            cookies=server_id_cookie
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "TREASURY_POST_TRANSACTION_DOCUMENT_REQUESTS_EXCEPTIONS"})
        return DOCUMENT_ATTACH_FAILED_REQUESTS_EXCEPTIONS
    # handle response code
    if response.status_code != 201:
        logger.error(
            "Incorrect upload status while attaching document to transaction",
            extra={
                "MESSAGE_ID": "ATTACH_DOC_UNSUCCESSFUL_STATUS",
                "STATUS_CODE": response.status_code,
                "TRANSACTION_ID": transaction_id,
                "RESPONSE_TEXT": response.text,
                "DOCUMENT_TITLE": data["title"],
            }
        )
        return response.status_code
    else:
        logger.info(
            "File {} was successful attached to {} transaction".format(data["title"], transaction_id),
            extra={"MESSAGE_ID": "SUCCESSFUL_DOC_ATTACHED"}
        )
        return ATTACH_DOCUMENT_TO_TRANSACTION_SUCCESSFUL_STATUS
