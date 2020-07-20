from celery_worker.celery import app
from celery_worker.locks import concurrency_lock, unique_task_decorator
from treasury.storage import get_contract_context, save_contract_context, update_organisations, get_organisation
from treasury.documents import prepare_documents
from treasury.templates import (
    render_contract_xml, render_change_xml, render_catalog_xml,
    prepare_context, prepare_contract_context, render_transactions_confirmation_xml
)
from treasury.api_requests import send_request, get_request_response, parse_organisations, prepare_request_data
from environment_settings import (
    TREASURY_RESPONSE_RETRY_COUNTDOWN, TREASURY_CATALOG_UPDATE_RETRIES,
    TREASURY_INT_START_DATE, API_HOST, API_VERSION, API_TOKEN
)
from celery.utils.log import get_task_logger
from tasks_utils.requests import (
    get_public_api_data, get_request_retry_countdown,
    ds_upload, get_json_or_retry, sign_data, get_exponential_request_retry_countdown
)
from tasks_utils.datetime import get_now
from datetime import timedelta
from uuid import uuid4
from treasury.exceptions import TransactionsQuantityServerErrorHTTPException
from treasury.domain.prtrans import save_transaction_xml, ds_upload, put_transaction, attach_doc_to_contract
from treasury.settings import (
    PUT_TRANSACTION_SUCCESSFUL_STATUS,
    ATTACH_DOCUMENT_TO_TRANSACTION_SUCCESSFUL_STATUS,
)
from collections import namedtuple

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

    # sign document
    sign = sign_data(self, document)  # TODO: get ready to increase READ_TIMEOUT inside

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

    # sign document
    sign = sign_data(self, document)

    # send request
    send_request(self, document, sign=sign, message_id=message_id, method_name="GetRef")

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


@app.task(bind=True, max_retries=10)
def process_transaction(self, transactions_data, source, message_id):
    #  celery tasks by default using json serializer, that serialize datetime to str inside transaction data

    transactions_ids = [record["ref"] for record in transactions_data]

    saved_document = save_transaction_xml(transactions_ids, source)
    transactions_statuses = []
    TransactionStatus = namedtuple('TransactionStatus', 'put attach final')

    for trans in transactions_data:
        put_transaction_status = put_transaction(trans)
        attach_doc_to_transaction_status = attach_doc_to_contract(
            saved_document['data'], trans['id_contract'], trans['ref']
        )
        if (
            put_transaction_status == PUT_TRANSACTION_SUCCESSFUL_STATUS and
            attach_doc_to_transaction_status == ATTACH_DOCUMENT_TO_TRANSACTION_SUCCESSFUL_STATUS
        ):
            final_status = True
        else:
            final_status = False
        trans_status = TransactionStatus(put_transaction_status, attach_doc_to_transaction_status, final_status)
        transactions_statuses.append(trans_status)
    logger.info(f"Transactions statuses after PUT and ATTACH DOC to API: {transactions_statuses}",
                extra={"MESSAGE_ID": "TREASURY_TRANSACTIONS_STATUSES"})
    final_statuses = [status.final for status in transactions_statuses]

    send_transactions_results.delay(final_statuses, transactions_data, message_id)


@app.task(bind=True, max_retries=10)
def send_transactions_results(self, transactions_statuses, transactions_data, message_id):
    successful_trans_quantity = transactions_statuses.count(True)
    transactions_quantity = len(transactions_data)

    if successful_trans_quantity == 0:
        status_id = -1  # no records processed
    elif successful_trans_quantity < transactions_quantity:
        status_id = 1  # some records are successfully processed
    elif successful_trans_quantity == transactions_quantity:
        status_id = 0  # all records are successfully processed
    else:
        raise TransactionsQuantityServerErrorHTTPException()

    transactions_values_sum = sum([trans['doc_sq'] for trans in transactions_data])

    xml_document = render_transactions_confirmation_xml(
        register_id=str(message_id),
        status_id=str(status_id),
        date=get_now().isoformat(),
        rec_count=str(successful_trans_quantity),
        reg_sum=str(transactions_values_sum)
    )
    sign = sign_data(self, xml_document)
    # sending changes
    # message_id = uuid4().hex

    logger.info(f'ConfirmPRTrans requested data: {xml_document}')
    send_request(self, xml_document, sign, message_id, method_name="ConfirmPRTrans")

    logger.info("PRTrans confirmation xml have been successful sent")
