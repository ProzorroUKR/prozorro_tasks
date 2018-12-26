from celery_worker.celery import app
from celery.utils.log import get_task_logger
from edr_bot.settings import (
    DOC_TYPE, IDENTIFICATION_SCHEME, DOC_AUTHOR,
    VERSION as EDR_BOT_VERSION,
    CONNECT_TIMEOUT, READ_TIMEOUT, DEFAULT_RETRY_AFTER,
    FILE_NAME, ID_PASSPORT_LEN,
)
from environment_settings import (
    API_HOST, API_TOKEN, PUBLIC_API_HOST, API_VERSION,
    EDR_API_HOST, EDR_API_PORT, EDR_API_VERSION, EDR_API_USER, EDR_API_PASSWORD,
    DS_HOST, DS_PORT, DS_USER, DS_PASSWORD,
)
from uuid import uuid4
import requests
import yaml
import io


logger = get_task_logger(__name__)

RETRY_REQUESTS_EXCEPTIONS = (
    requests.exceptions.Timeout,
    requests.exceptions.ConnectionError,
)


@app.task(bind=True)
def process_tender(self, tender_id):
    url = "{host}/api/{version}/tenders/{tender_id}".format(
        host=PUBLIC_API_HOST,
        version=API_VERSION,
        tender_id=tender_id,
    )

    try:
        response = requests.get(
            url,
            headers={"X-Client-Request-ID": uuid4().hex},
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc)
        raise self.retry(exc=exc)
    else:
        if response.status_code != 200:
            logger.error("Unexpected status code {} while getting tender {}".format(
                response.status_code, tender_id
            ))
            raise self.retry(countdown=response.headers.get('Retry-After', DEFAULT_RETRY_AFTER))

        tender_data = response.json()["data"]

        # --------
        if 'awards' in tender_data:
            for award in tender_data['awards']:
                if should_process_item(award):
                    for supplier in award['suppliers']:
                        process_award_supplier(response, tender_data, award, supplier)

        elif 'qualifications' in tender_data:
            for qualification in tender_data['qualifications']:
                if should_process_item(qualification):
                    process_qualification(response, tender_data, qualification)


def should_process_item(item):
    return (item['status'] == 'pending' and
            not any(document.get('documentType') == DOC_TYPE
                    for document in item.get('documents', [])))


def check_related_lot_status(tender, award):
    """Check if related lot not in status cancelled"""
    lot_id = award.get('lotID')
    if lot_id:
        if [l['status'] for l in tender.get('lots', []) if l['id'] == lot_id][0] != 'active':
            return False
    return True


def process_award_supplier(response, tender, award, supplier):
    code = str(supplier['identifier']['id'])
    if not code.isdigit():
        logger.warning('Tender {} award {} identifier {} is not digit.'.format(
            tender['id'], award["id"], code
        ))
    elif supplier['identifier']['scheme'] != IDENTIFICATION_SCHEME:
        logger.warning("Tender {} bid {} award {} identifier schema isn't UA-EDR".format(
            tender['id'], award['bid_id'], award['id']
        ))
    elif not check_related_lot_status(tender, award):
        logger.warning("Tender {} bid {} award {} related lot has been cancelled".format(
            tender['id'], award['bid_id'], award['id']
        ))
    else:
        get_edr_data.delay(code, response.headers['X-Request-ID'], tender['id'], "award", award['id'])


def process_qualification(response, tender, qualification):
    appropriate_bid = [b for b in tender['bids'] if b['id'] == qualification['bidID']][0]
    code = str(appropriate_bid['tenderers'][0]['identifier']['id'])
    if not code.isdigit():
        logger.warning('Tender {} qualification {} identifier {} is not digit.'.format(
            tender['id'], qualification["id"], code
        ))
    elif appropriate_bid['tenderers'][0]['identifier']['scheme'] != IDENTIFICATION_SCHEME:
        logger.warning("Tender {} bid {} award {} identifier schema isn't UA-EDR".format(
            tender['id'], qualification['bidID'], qualification['id']
        ))
    else:
        get_edr_data.delay(code, response.headers['X-Request-ID'], tender['id'], "qualification", qualification['id'])


# ------- GET EDR DATA

@app.task(bind=True)
def get_edr_data(self, code, request_id, tender_id, item_name, item_id):
    meta = {
        'id': uuid4().hex,
        'author': DOC_AUTHOR,
        'sourceRequests': [request_id],
        'version': EDR_BOT_VERSION,
    }
    param = 'id' if code.isdigit() and len(code) != ID_PASSPORT_LEN else 'passport'
    url = "{host}:{port}/api/{version}/verify?{param}={code}".format(
        host=EDR_API_HOST, port=EDR_API_PORT, version=EDR_API_VERSION,
        param=param,
        code=code,
    )
    try:
        response = requests.get(
            url,
            auth=(EDR_API_USER, EDR_API_PASSWORD),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={"X-Client-Request-ID": meta["id"]}
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc)
        raise self.retry(exc=exc)
    else:
        resp_json = response.json()
        data_list = []

        if (response.status_code == 404 and isinstance(resp_json, dict)
           and len(resp_json.get('errors', "")) > 0 and len(resp_json.get('errors')[0].get('description', '')) > 0
           and resp_json.get('errors')[0].get('description')[0].get('error', {}).get('code', '') == u"notFound"):
            logger.warning('Empty response for {} code {}={}.'.format(tender_id, param, code))

            file_content = resp_json.get('errors')[0].get('description')[0]
            file_content['meta'].update(meta)
            data_list.append(file_content)

        elif response.status_code == 200:

            document_id = meta["id"]

            for i, obj in enumerate(resp_json['data']):

                if len(resp_json['data']) > 1:
                    meta_id = '{}.{}.{}'.format(document_id, len(resp_json['data']), i + 1)
                else:
                    meta_id = document_id

                source_date = None
                if len(resp_json['meta']['detailsSourceDate']) >= i + 1:
                    source_date = resp_json['meta']['detailsSourceDate'][i]

                file_content = {
                    'meta': {
                        'sourceDate': source_date
                    },
                    'data': obj
                }
                file_content['meta'].update(meta)
                file_content['meta']['id'] = meta_id
                data_list.append(file_content)
        else:
            raise self.retry(countdown=response.headers.get('Retry-After', DEFAULT_RETRY_AFTER))

        for data in data_list:
            upload_to_doc_service.delay(data=data, tender_id=tender_id, item_name=item_name, item_id=item_id)


# --------- UPLOAD TO DS
@app.task(bind=True)
def upload_to_doc_service(self, data, tender_id, item_name, item_id):

    temporary_file = io.BytesIO()
    temporary_file.name = FILE_NAME
    temporary_file.write(
        yaml.safe_dump(data, allow_unicode=True, default_flow_style=False)
    )
    temporary_file.seek(0)

    files = {'file': (FILE_NAME, temporary_file, 'application/yaml')}

    try:
        response = requests.post(
            '{host}:{port}/upload'.format(host=DS_HOST, port=DS_PORT),
            auth=(DS_USER, DS_PASSWORD),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            files=files,
            headers={'X-Client-Request-ID': data['meta']['id']}
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc)
        raise self.retry(exc=exc)
    else:
        if response.status_code != 200:
            logger.error("Incorrect upload status for doc {}".format(data['meta']['id']))
            raise self.retry(countdown=response.headers.get('Retry-After', DEFAULT_RETRY_AFTER))

        response_json = response.json()
        response_json['meta'] = {'id': data['meta']['id']}
        attach_doc_to_tender.delay(response_json, tender_id, item_name, item_id)


# ---------- ATTACH DOCUMENT TO ITS TENDER
@app.task(bind=True)
def attach_doc_to_tender(self, data, tender_id, item_name, item_id):
    document_data = data['data']
    document_data["documentType"] = DOC_TYPE

    url = "{host}/api/{version}/tenders/{tender_id}/{item_name}s/{item_id}/documents".format(
        host=API_HOST,
        version=API_VERSION,
        item_name=item_name,
        item_id=item_id,
        tender_id=tender_id,
    )

    # get SERVER_ID cookie
    try:
        head_response = requests.head(
            url,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={
                'Authorization': 'Bearer {}'.format(API_TOKEN),
                'X-Client-Request-ID': data['meta']['id'],
            }
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc)
        raise self.retry(exc=exc)
    else:

        # post document
        try:
            response = requests.post(
                url,
                json={'data': document_data},
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                headers={
                    'Authorization': 'Bearer {}'.format(API_TOKEN),
                    'X-Client-Request-ID': data['meta']['id'],
                },
                cookies=head_response.cookies,
            )
        except RETRY_REQUESTS_EXCEPTIONS as exc:
            logger.exception(exc)
            raise self.retry(exc=exc)
        else:

            # handle response code
            if response.status_code == 422:
                logger.error("Incorrect document data while attaching doc {} to tender {}".format(
                    data['meta']['id'], tender_id
                ))

            elif response.status_code != 200:
                logger.error("Incorrect upload status while attaching doc {} to tender {}".format(
                    data['meta']['id'], tender_id
                ))
                raise self.retry(countdown=response.headers.get('Retry-After', DEFAULT_RETRY_AFTER))
