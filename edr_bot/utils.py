from datetime import datetime

import requests

from flask_restx._http import HTTPStatus
from celery.utils.log import get_task_logger
from pytz import UTC

from app.exceptions import abort_json
from edr_bot.settings import EDR_REGISTRATION_STATUSES, EDR_IDENTIFICATION_SCHEMA, EDR_ACTIVITY_KIND_SCHEME
from environment_settings import EDR_API_DIRECT_VERSION, EDR_API_DIRECT_URI, EDR_API_DIRECT_TOKEN, \
    CONNECT_TIMEOUT, READ_TIMEOUT, EDR_API_CACHE_TIMEOUT, TIMEZONE

logger = get_task_logger(__name__)


def get_edr_data(subjects_url):
    url = f"{EDR_API_DIRECT_URI}/{EDR_API_DIRECT_VERSION}/{subjects_url}"
    return requests.get(
        url,
        timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        headers={
            "Accept": "application/json",
            "Authorization": f"Token {EDR_API_DIRECT_TOKEN}"
        }
    )


def get_edr_subject_details_data(edr_unique_id):
    """Get detailed data from EDR API by code (paid requests)"""
    return get_edr_data(f"subjects/{edr_unique_id}")


def get_edr_subject_data(param, code):
    """Get non-detailed data from EDR API by code (non-paid requests)"""
    return get_edr_data(f"subjects?{param}={code}")


def meta_data(date):
    """return sourceDate in ISO 8601format """
    return datetime.strptime(date, '%a, %d %b %Y %H:%M:%S %Z').replace(tzinfo=UTC).isoformat()


def prepare_data(data):
    return {
        'x_edrInternalId': data.get('id'),
        'registrationStatus': EDR_REGISTRATION_STATUSES.get(data.get('state'), 'other'),
        'registrationStatusDetails': data.get('state_text'),
        'identification': {
            'schema': EDR_IDENTIFICATION_SCHEMA,
            'id': data.get('code'),
            'legalName': data.get('name'),
            'url': data.get('url'),
        }
    }


def get_address(data):
    address = data.get('address') or {}
    return {
        'streetAddress': address.get('address'),
        'postalCode': address.get('zip'),
        'countryName': address.get('country'),
    }


def remove_null_fields(data):
    """Remove all keys with 'None' values"""
    if isinstance(data, dict):
        keys_to_delete = []
        for k, v in data.items():
            if isinstance(v, dict):
                remove_null_fields(v)
            elif isinstance(v, list):
                for element in v:
                    remove_null_fields(element)
            if v is None or v == {} or v == []:
                keys_to_delete.append(k)
        for k in keys_to_delete:
            del data[k]
    elif isinstance(data, list):
        for element in data:
            remove_null_fields(element)
    return data


def prepare_data_details(data):
    if EDR_API_DIRECT_VERSION == "2.0":
        result = data
    else:
        founders = data.get('founders', [])
        for founder in founders:
            founder['address'] = get_address(founder)
        additional_activity_kinds = []
        primary_activity_kind = {}
        for activity_kind in data.get('activity_kinds', []):
            if activity_kind.get('is_primary'):
                primary_activity_kind = {'id': activity_kind.get('code'),
                                         'scheme': EDR_ACTIVITY_KIND_SCHEME,
                                         'description': activity_kind.get('name')}
            else:
                additional_activity_kinds.append({'id': activity_kind.get('code'),
                                                  'scheme': EDR_ACTIVITY_KIND_SCHEME,
                                                  'description': activity_kind.get('name')})
        result = {
            'name': data.get('names').get('short') if data.get('names') else None,
            'registrationStatus': EDR_REGISTRATION_STATUSES.get(data.get('state')),
            'registrationStatusDetails': data.get('state_text'),
            'identification': {
                'scheme': EDR_IDENTIFICATION_SCHEMA,
                'id': data.get('code'),
                'legalName': data.get('names').get('display') if data.get('names') else None,
            },
            'founders': founders,
            'management': data.get('management'),
            'activityKind': primary_activity_kind or None,
            'additionalActivityKinds': additional_activity_kinds or None,
            'address': get_address(data),
        }
    return remove_null_fields(result)


def handle_error(response):
    if response.headers['Content-Type'] != 'application/json':
        abort_json(
            code=HTTPStatus.FORBIDDEN,
            error_message={"location": "request", "name": "ip", "description": [{"message": "Forbidden"}]},
        )
    if response.status_code == 429:
        seconds_to_wait = response.headers.get('Retry-After')
        abort_json(
            code=HTTPStatus.TOO_MANY_REQUESTS,
            error_message={
                "location": "body",
                "name": "data",
                "description": [{"message": f"Retry request after {seconds_to_wait} seconds."}],
            },
            headers={'Retry-After': seconds_to_wait},
        )
    elif response.status_code == 502:
        abort_json(
            code=HTTPStatus.FORBIDDEN,
            error_message={
                "location": "body",
                "name": "data",
                "description": [{"message": "Service is disabled or upgrade."}],
            },
        )
    abort_json(
        code=HTTPStatus.FORBIDDEN,
        error_message={"location": "body", "name": "data", "description": response.json()['errors']},
    )


def user_details(internal_ids):
    """Composes array of detailed reference files"""
    data = []
    details_source_date = []
    for internal_id in internal_ids:
        try:
            response = get_edr_subject_details_data(internal_id)
        except (requests.exceptions.ReadTimeout,
                requests.exceptions.ConnectTimeout):
            abort_json(
                code=HTTPStatus.FORBIDDEN,
                error_message={"location": "body", "name": "data", "description": [{"message": "Gateway Timeout Error"}]},
            )
        if response.status_code != 200:
            return handle_error(response)
        else:
            logger.info(f"Return detailed data from EDR service for {internal_id}")
            data.append(prepare_data_details(response.json()))
            details_source_date.append(meta_data(response.headers['Date']))
    return {"data": data, "meta": {"sourceDate": details_source_date[-1], "detailsSourceDate": details_source_date}}


def form_edr_response(response, code, role):
    """Form data after making a request to EDR"""
    from app.app import cache
    if response.status_code == 200:
        logger.info(f"Response code {response.status_code} for code {code}")
        data = response.json()
        if not data:
            logger.warning(f"Accept empty response from EDR service for {code}")
            abort_json(
                code=HTTPStatus.NOT_FOUND,
                error_message={
                    "location": "body",
                    "name": "data",
                    "description": [{
                        "meta": {"sourceDate": meta_data(response.headers['Date'])},
                        "error": {
                            "errorDetails": "Couldn't find this code in EDR.",
                            "code": "notFound"
                        }
                    }]},
            )
        res = {'data': [prepare_data(d) for d in data], 'meta': {'sourceDate': meta_data(response.headers['Date'])}}
        cache.set(f"verify_{EDR_API_DIRECT_VERSION}_{code}", res, EDR_API_CACHE_TIMEOUT)
        if role == 'robot':  # get details for edr-bot
            data_details = user_details([obj['id'] for obj in data])
            if not data_details.get("errors"):
                cache.set(f"details_{EDR_API_DIRECT_VERSION}_{code}", data_details, timeout=EDR_API_CACHE_TIMEOUT)
            return data_details
        return res
    else:
        return handle_error(response)


def cached_details(code):
    """Return cached data from EDR to robot"""
    from app.app import cache
    if cached_details_data := cache.get(f"details_{EDR_API_DIRECT_VERSION}_{code}"):
        logger.info(f"Code {code} was found in cache at details")
        return cached_details_data
    elif cached_verify_data := cache.get(f"verify_{EDR_API_DIRECT_VERSION}_{code}"):
        data_details = user_details([obj['x_edrInternalId'] for obj in cached_verify_data['data']])
        if not data_details.get("errors"):
            cache.set(f"details_{EDR_API_DIRECT_VERSION}_{code}", data_details, timeout=EDR_API_CACHE_TIMEOUT)
        return data_details


def read_json(name):
    import os.path
    from json import loads
    curr_dir = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(curr_dir, name)
    with open(file_path) as lang_file:
        data = lang_file.read()
    return loads(data)


TEST_DATA_VERIFY = read_json('tests/data/test_data_verify.json')
TEST_DATA_DETAILS = read_json('tests/data/test_data_details.json')


def get_sandbox_data(code, role):
    """ If in sandbox_mode we reached requests limit, then we return sandbox data"""
    if role == 'robot' and TEST_DATA_DETAILS.get(code):
        logger.info(f'Return test data for {code} for robot')
        data = []
        details_source_date = []
        for i in range(len(TEST_DATA_DETAILS[code])):
            data.append(prepare_data_details(TEST_DATA_DETAILS[code][i]))
            details_source_date.append(datetime.now(tz=TIMEZONE).isoformat())
        return {
            'meta': {'sourceDate': details_source_date[0], 'detailsSourceDate': details_source_date},
            'data': data,
        }
    elif TEST_DATA_VERIFY.get(code):
        logger.info('Return test data for {} for platform'.format(code))
        return {
            'data': [prepare_data(d) for d in TEST_DATA_VERIFY[code]],
            'meta': {'sourceDate': datetime.now(tz=TIMEZONE).isoformat()},
        }
    else:
        logger.info(f"Code {code} not found in test data for {role}, returning 404")
        abort_json(
            code=HTTPStatus.NOT_FOUND,
            error_message={
                "location": "body",
                "name": "data",
                "description": [{
                    "meta": {"sourceDate": datetime.now(tz=TIMEZONE).isoformat()},
                    "error": {
                        "errorDetails": "Couldn't find this code in EDR.",
                        "code": "notFound"
                    }
                }]},
        )
