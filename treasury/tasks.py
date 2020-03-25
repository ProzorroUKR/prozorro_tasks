from celery_worker.celery import app
from celery_worker.locks import concurrency_lock, unique_task_decorator
from treasury.storage import get_contract_context, save_contract_context, update_organisations, get_organisation
from treasury.documents import prepare_documents
from treasury.templates import render_contract_xml, render_change_xml, render_catalog_xml, \
    prepare_context, prepare_contract_context
from treasury.api_requests import send_request, get_request_response, parse_organisations
from environment_settings import TREASURY_RESPONSE_RETRY_COUNTDOWN, TREASURY_CATALOG_UPDATE_RETRIES, \
    TREASURY_INT_START_DATE
from celery.utils.log import get_task_logger
from tasks_utils.requests import get_public_api_data
from tasks_utils.datetime import get_now
from datetime import timedelta
from uuid import uuid4


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


@app.task(bind=True, max_retries=None)
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

    # with open(f"contract-{contract_id}.xml", "wb") as f:  # TODO remove
    #     f.write(document)

    # sending changes
    message_id = uuid4().hex
    send_request(self, document, message_id=message_id, method_name="PrContract")
    logger.info(
        "Contract details sent",
        extra={"MESSAGE_ID": "TREASURY_CONTRACT_SENT", "CONTRACT_ID": contract_id, "REQUEST_ID": message_id}
    )


@app.task(bind=True, max_retries=None)
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

    # with open(f"change-{change_id}.xml", "wb") as f:  # TODO remove
    #     f.write(document)

    # sending request
    message_id = uuid4().hex
    send_request(self, document, message_id=message_id, method_name="PrChange")
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
