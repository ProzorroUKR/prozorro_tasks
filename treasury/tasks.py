from celery_worker.celery import app
from celery_worker.locks import concurrency_lock, unique_task_decorator
from treasury.storage import get_contract_context, save_contract_context, update_organisations, get_organisation
from treasury.documents import prepare_documents
from treasury.templates import render_contract_xml, render_change_xml, render_catalog_xml, \
    prepare_context, prepare_contract_context
from treasury.api_requests import send_request, get_request_response, parse_organisations
from environment_settings import TREASURY_RESPONSE_RETRY_COUNTDOWN, TREASURY_CATALOG_UPDATE_RETRIES, \
    TREASURY_INT_START_DATE, API_HOST, API_VERSION, API_TOKEN
from celery.utils.log import get_task_logger
from tasks_utils.requests import (
    get_public_api_data, get_request_retry_countdown, ds_upload, get_json_or_retry, sign_data
)
from tasks_utils.settings import CONNECT_TIMEOUT, READ_TIMEOUT, RETRY_REQUESTS_EXCEPTIONS
from tasks_utils.datetime import get_now
from datetime import timedelta
from uuid import uuid4
import requests


logger = get_task_logger(__name__)


@app.task(bind=True, max_retries=None)
@concurrency_lock
def check_contract(self, contract_id):
    """
    this task will be triggered by contract change
    checks if the contract details and changes haven't been sent
    schedule the following task to send them
    The maximum mongodb BSON document size is 16 megabytes,
    so the final xml with b64 of files can exceed the limit if we save them
    :param self:
    :param contract_id:
    :return:
    """
    contract = get_public_api_data(self, contract_id, "contract")
    if contract["dateSigned"] < TREASURY_INT_START_DATE:
        return logger.debug(f"Skipping contract {contract['id']} signed at {contract['dateSigned']}",
                            extra={"MESSAGE_ID": "TREASURY_SKIP_CONTRACT"})

    identifier = contract["procuringEntity"]["identifier"]
    if contract["status"] != "active" or identifier["scheme"] != "UA-EDR":
        return logger.debug(f"Skipping {contract['status']} contract {contract['id']} with identifier {identifier}",
                            extra={"MESSAGE_ID": "TREASURY_SKIP_CONTRACT"})

    org = get_organisation(self, identifier["id"])
    if org is None:
        return logger.debug(f"Skipping contract {contract['id']} with identifier {identifier} not on the list",
                            extra={"MESSAGE_ID": "TREASURY_SKIP_CONTRACT"})

    context = get_contract_context(self, contract["id"])
    if context:
        change_ids = {c["id"] for c in contract.get("changes", "")}
        sent_change_ids = {c["id"] for c in context["contract"].get("changes", "")}
        new_change_ids = change_ids - sent_change_ids
        if not new_change_ids:
            return logger.info(
                f"Skip contract {contract['id']}: all its changes have been sent",
                extra={"MESSAGE_ID": "TREASURY_NO_NEED_UPDATE"}
            )

        # if we here, then we need to send only change.xml request for every new change
        prepare_contract_context(contract)

        # update contract data and changes
        save_contract_context(self, contract["id"], {"contract": contract})

        # schedule tasks
        for change_id in sorted(new_change_ids):
            send_change_xml.delay(contract["id"], change_id)
    else:
        tender = get_public_api_data(self, contract["tender_id"], "tender")
        if "plans" in tender:
            plan = get_public_api_data(self, tender["plans"][0]["id"], "plan")
        else:
            plan = None
            logger.warning(
                f"Cannot find plan for {contract['id']} and tender {tender['id']}",
                extra={"MESSAGE_ID": "TREASURY_PLAN_LINK_MISSED"}
            )
        context = prepare_context(self, contract, tender, plan)
        save_contract_context(self, contract["id"], context)
        send_contract_xml.delay(contract["id"])


@app.task(bind=True, max_retries=1000)
@concurrency_lock
@unique_task_decorator
def send_contract_xml(self, contract_id):
    """
    Gets all api data from prepared mongodb document
    Downloads the documents
    Builds the xml
    Sends the xml to the treasury api
    :param self:
    :param contract_id:
    :return:
    """
    context = get_contract_context(self, contract_id)
    # b64 encode documents
    prepare_documents(self, context["contract"])
    for change in context["contract"].get("changes", ""):
        prepare_documents(self, change)
    # building request
    document = render_contract_xml(context)

    # with open(f"data_{contract_id}.xml", "wb") as f:
    #     f.write(document)

    # sign document
    sign = sign_data(self, document)   # TODO: get ready to increase READ_TIMEOUT inside

    # with open(f"sign_{contract_id}.xml", "wb") as f:
    #     f.write(sign)

    # sending changes
    message_id = uuid4().hex
    send_request(self, document, sign=sign, message_id=message_id, method_name="PrContract")
    logger.info(
        "Contract details sent",
        extra={"MESSAGE_ID": "TREASURY_CONTRACT_SENT", "CONTRACT_ID": contract_id, "REQUEST_ID": message_id}
    )


@app.task(bind=True, max_retries=1000)
@concurrency_lock
@unique_task_decorator
def send_change_xml(self, contract_id, change_id):
    context = get_contract_context(self, contract_id)

    for change in context["contract"]["changes"]:
        if change["id"] == change_id:
            break
    else:
        return logger.critical(f"Scheduled sending change {change_id} that is not in the context")

    # building request
    prepare_documents(self, change)
    context["change"] = change
    document = render_change_xml(context)

    # sign document
    sign = sign_data(self, document)

    # sending request
    message_id = uuid4().hex
    send_request(self, document, sign=sign, message_id=message_id, method_name="PrChange")
    logger.info(
        "Contract change sent",
        extra={"MESSAGE_ID": "TREASURY_CONTRACT_CHANGE_SENT",
               "CONTRACT_ID": contract_id,
               "CHANGE_ID": change_id,
               "REQUEST_ID": message_id}
    )


@app.task(bind=True, max_retries=TREASURY_CATALOG_UPDATE_RETRIES)
def request_org_catalog(self):
    document = render_catalog_xml(dict(catalog_id="RefOrgs"))
    message_id = uuid4().hex
    send_request(self, document, message_id=message_id, method_name="GetRef")

    expected_response_time = get_now() + timedelta(seconds=3 * 60)
    receive_org_catalog.apply_async(
        eta=expected_response_time,  # requests earlier return 500 status code
        kwargs=dict(
            message_id=message_id,
        )
    )


@app.task(bind=True, max_retries=TREASURY_CATALOG_UPDATE_RETRIES)
def receive_org_catalog(self, message_id):
    response = get_request_response(self, message_id=message_id)
    if response is None:  # isn't ready ?
        logger_method = logger.warning if self.request.retries > 10 else logger.error
        logger_method(f"Empty response for org catalog request",
                      extra={"MESSAGE_ID": "TREASURY_ORG_CATALOG_EMPTY"})
        raise self.retry(countdown=TREASURY_RESPONSE_RETRY_COUNTDOWN)

    result = update_organisations(
        self,
        parse_organisations(response)
    )
    logger.info(f"Updated org catalog: {result}",
                extra={"MESSAGE_ID": "TREASURY_ORG_CATALOG_UPDATE"})


@app.task(bind=True, max_retries=1000)
def save_transaction(self, source, transaction):
    document = ds_upload(
        self,
        file_name=f"Transaction_{transaction['transaction_id']}_{transaction['data']['status']}.xml",
        file_content=source
    )
    document["documentType"] = "dataSource"
    transaction["data"]["documents"] = [document]
    put_transaction.delay(**transaction)


@app.task(bind=True, max_retries=1000)
def put_transaction(self, contract_id, transaction_id, data):
    url = f"{API_HOST}/api/{API_VERSION}/contract/{contract_id}/transactions/{transaction_id}"
    session = requests.Session()
    log_context = {
        "CONTRACT_ID": contract_id,
        "TRANSACTION_ID": transaction_id,
    }
    try:
        get_response = session.head(
            url,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={
                'Authorization': 'Bearer {}'.format(API_TOKEN),
            }
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.warning(
            "Request exception",
            extra={
                "MESSAGE_ID": "TREASURY_TRANS_EXCEPTION",
                "EXC": exc,
                **log_context
            }
        )
        raise self.retry(exc=exc)
    else:
        log_context["HEAD_RESPONSE_STATUS"] = get_response.status_code
        if get_response.status_code == 200:  # update
            request_method = session.patch
            json_resp = get_json_or_retry(self, get_response)
            docs_len = len(json_resp.get("data", {}).get("documents", ""))
            data["documents"] = [{} for _ in range(docs_len)] + data["documents"]
        else:  # create
            request_method = session.put

        try:
            response = request_method(
                url,
                json={'data': data},
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                headers={'Authorization': 'Bearer {}'.format(API_TOKEN)},
            )
        except RETRY_REQUESTS_EXCEPTIONS as exc:
            logger.exception(exc, extra={"MESSAGE_ID": "TREASURY_TRANS_EXCEPTION", **log_context})
            raise self.retry(exc=exc)
        else:
            log_context["RESPONSE_STATUS"] = response.status_code
            if response.status_code == 422:
                logger.error(
                    "Incorrect data",
                    extra={"MESSAGE_ID": "TREASURY_TRANS_ERROR", **log_context}
                )
            elif response.status_code not in (201, 200):
                logger.error(
                    "Unexpected status",
                    extra={
                        "MESSAGE_ID": "TREASURY_TRANS_UNSUCCESSFUL_STATUS",
                        "RESPONSE_TEXT": response.text, **log_context
                    })
                raise self.retry(countdown=get_request_retry_countdown(response))
            else:
                logger.info(
                    "Transaction successfully saved",
                    extra={"MESSAGE_ID": "TREASURY_TRANS_SUCCESSFUL", **log_context}
                )
