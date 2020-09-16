from celery_worker.celery import app, formatter
from celery.utils.log import get_task_logger
from environment_settings import (
    API_HOST, API_TOKEN, API_VERSION,
    DS_HOST, DS_USER, DS_PASSWORD,
)
from tasks_utils.settings import CONNECT_TIMEOUT, READ_TIMEOUT, DEFAULT_RETRY_AFTER, RETRY_REQUESTS_EXCEPTIONS
from tasks_utils.results_db import (
    get_task_result,
    save_task_result,
)
import requests
import base64


logger = get_task_logger(__name__)


ATTACH_DOC_MAX_RETRIES = 100


@app.task(bind=True)
@formatter.omit(["content"])
def upload_to_doc_service(self, name, content, doc_type,
                          tender_id, item_name, item_id):

    # check if the file has been already uploaded
    # will retry the task until mongodb returns either doc or None
    task_args = name, content, doc_type, tender_id, item_name, item_id
    result = get_task_result(self, task_args)
    if result is None:
        try:
            response = requests.post(
                '{host}/upload'.format(host=DS_HOST),
                auth=(DS_USER, DS_PASSWORD),
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                files={'file': (name, base64.b64decode(content))},
            )
        except RETRY_REQUESTS_EXCEPTIONS as exc:
            logger.exception(exc, extra={"MESSAGE_ID": "POST_DOC_API_ERROR"})
            raise self.retry(exc=exc)
        else:
            if response.status_code != 200:
                logger.error("Incorrect upload status for doc {}".format(name),
                             extra={"MESSAGE_ID": "POST_DOC_API_ERROR",
                                    "STATUS_CODE": response.status_code})
                raise self.retry(countdown=response.headers.get('Retry-After', DEFAULT_RETRY_AFTER))

            response_json = response.json()
            result = response_json["data"]
            result["documentType"] = doc_type

            # save response to mongodb, so that the file won't be uploaded again
            # fail silently: if mongodb isn't available, the task will neither fail nor retry
            # in worst case there might be a duplicate attached to the tender
            uid = save_task_result(self, result, task_args)
            logger.info("Saved document with uid {} for {} {} {}".format(
                uid, tender_id, item_name, item_id),
                extra={"MESSAGE_ID": "SAVE_UPLOAD_DOC_RESULTS_SUCCESS"}
            )

    attach_doc_to_tender.delay(
        data=result,
        tender_id=tender_id,
        item_name=item_name,
        item_id=item_id,
    )


@app.task(bind=True, max_retries=ATTACH_DOC_MAX_RETRIES)
def attach_doc_to_tender(self, data, tender_id, item_name, item_id):

    task_args = data, tender_id, item_name, item_id
    result = get_task_result(self, task_args)
    if result:
        logger.info("File has been already attached to the tender: {} {} {}".format(
            tender_id, item_name, item_id), extra={"MESSAGE_ID": "DOC_ALREADY_ATTACHED"})
    else:

        url = "{host}/api/{version}/tenders/{tender_id}/{item_name}s/{item_id}/documents".format(
            host=API_HOST,
            version=API_VERSION,
            tender_id=tender_id,
            item_name=item_name,
            item_id=item_id,
        )
        # get SERVER_ID cookie
        try:
            head_response = requests.head(
                url,
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                headers={
                    'Authorization': 'Bearer {}'.format(API_TOKEN),
                }
            )
        except RETRY_REQUESTS_EXCEPTIONS as exc:
            logger.exception(exc, extra={"MESSAGE_ID": "ATTACH_DOC_HEAD_ERROR"})
            raise self.retry(exc=exc)
        else:
            # post document
            try:
                response = requests.post(
                    url,
                    json={'data': data},
                    timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                    headers={
                        'Authorization': 'Bearer {}'.format(API_TOKEN),
                    },
                    cookies=head_response.cookies,
                )
            except RETRY_REQUESTS_EXCEPTIONS as exc:
                logger.exception(exc, extra={"MESSAGE_ID": "ATTACH_DOC_POST_ERROR"})
                raise self.retry(exc=exc)
            else:
                # handle response code
                if response.status_code == 422:
                    logger.error("Incorrect document data while attaching doc {} to tender {}: {}".format(
                        data["title"], tender_id, response.text
                    ), extra={"MESSAGE_ID": "ATTACH_DOC_DATA_ERROR"})
                elif response.status_code == 403:
                    logger.warning(
                        "Can't upload document: {}".format(response.json),
                        extra={"MESSAGE_ID": "ATTACH_DOC_UNSUCCESSFUL_STATUS", "STATUS_CODE": response.status_code}
                    )
                elif response.status_code != 201:
                    logger.warning("Incorrect upload status while attaching doc {} to tender {}: {}".format(
                        data["title"], tender_id, response.text
                    ), extra={"MESSAGE_ID": "ATTACH_DOC_UNSUCCESSFUL_STATUS", "STATUS_CODE": response.status_code})
                    raise self.retry(countdown=response.headers.get('Retry-After', DEFAULT_RETRY_AFTER))
                else:
                    uid = save_task_result(self, True, task_args)
                    logger.info(
                        "File attached uid={} for {} {} {}".format(uid, tender_id, item_name, item_id),
                        extra={"MESSAGE_ID": "SUCCESSFUL_DOC_ATTACHED"}
                    )
