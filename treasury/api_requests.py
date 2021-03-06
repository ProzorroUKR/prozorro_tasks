from environment_settings import (
    TREASURY_WSDL_URL, TREASURY_USER, TREASURY_PASSWORD, TREASURY_SKIP_REQUEST_VERIFY,
    CONNECT_TIMEOUT, READ_TIMEOUT,
)
from tasks_utils.requests import (
    RETRY_REQUESTS_EXCEPTIONS,
    get_exponential_request_retry_countdown,
    get_task_retry_logger_method,
)
from celery.utils.log import get_task_logger
from zeep import Client
from zeep.transports import Transport
from lxml import etree
from requests import Session
import base64

from tasks_utils.settings import DEFAULT_HEADERS

logger = get_task_logger(__name__)


def get_wsdl_client(task):
    transport = Transport(timeout=CONNECT_TIMEOUT,
                          operation_timeout=READ_TIMEOUT)
    try:
        client = Client(TREASURY_WSDL_URL, transport=transport)
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "TREASURY_REQUEST_EXCEPTION"})
        raise task.retry(exc=exc, countdown=get_exponential_request_retry_countdown(task))
    return client


# -- sending requests --

def send_request(task, xml, sign="", message_id=None, method_name="GetRef"):
    request_data = prepare_request_data(task, xml, sign, message_id, method_name)

    session = Session()
    session.headers.update(DEFAULT_HEADERS)
    if TREASURY_SKIP_REQUEST_VERIFY:
        session.verify = False
    try:
        response = session.post(
            TREASURY_WSDL_URL,
            data=request_data,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={
                'content-type': 'text/xml',
                **DEFAULT_HEADERS,
            },
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "TREASURY_REQUEST_EXCEPTION"})
        raise task.retry(exc=exc, countdown=get_exponential_request_retry_countdown(task))
    else:
        if response.status_code != 200:
            logger_method = get_task_retry_logger_method(task, logger)
            logger_method(
                f"Unexpected status code {response.status_code}:{response.content}",
                extra={
                    "MESSAGE_ID": "TREASURY_UNSUCCESSFUL_STATUS_CODE",
                    "STATUS_CODE": response.status_code,
                })
        else:
            code, text = parse_request_response(response.content)
            if code == 0:
                return code, text  # success
            logger.error(
                f"Unexpected code {code}:{text} while sending request",
                extra={"MESSAGE_ID": "TREASURY_UNSUCCESSFUL_CODE",
                       "CODE": code})
        raise task.retry(countdown=get_exponential_request_retry_countdown(task, response))


def prepare_request_data(task, xml, sign, message_id, method_name):
    # prepare request message
    client = get_wsdl_client(task)
    factory = client.type_factory("ns0")
    message = factory.RequestMessage(
        UserLogin=TREASURY_USER,
        UserPassword=TREASURY_PASSWORD,
        MessageId=message_id,
        MethodName=method_name,
        Data=base64.b64encode(xml),
        DataSign=base64.b64encode(sign),
    )
    message_node = client.create_message(client.service, 'SendRequest', message)
    return etree.tostring(message_node)


def parse_request_response(resp):
    r = etree.fromstring(resp)
    response_tag = r[0][0]
    code = response_tag.find(".//ResultCode", namespaces=response_tag.nsmap)
    message = response_tag.find(".//ResultMessage", namespaces=response_tag.nsmap)
    if code is not None:
        code = code.text
        try:
            code = int(code)
        except ValueError:
            pass
    return code, message.text


# -- receiving replies --

def prepare_get_response_data(task, message_id):
    client = get_wsdl_client(task)
    factory = client.type_factory("ns0")
    message = factory.RequestMessage(
        UserLogin=TREASURY_USER,
        UserPassword=TREASURY_PASSWORD,
        MessageId=message_id,
    )
    message_node = client.create_message(client.service, 'GetResponse', message)
    return etree.tostring(message_node)


def get_request_response(task, message_id):
    request_data = prepare_get_response_data(task, message_id)
    session = Session()
    session.headers.update(DEFAULT_HEADERS)
    if TREASURY_SKIP_REQUEST_VERIFY:
        session.verify = False
    try:
        response = session.post(
            TREASURY_WSDL_URL,
            data=request_data,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={
                'content-type': 'text/xml',
                **DEFAULT_HEADERS,
            },
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "TREASURY_REQUEST_EXCEPTION"})
        raise task.retry(exc=exc, countdown=get_exponential_request_retry_countdown(task))
    else:
        if response.status_code != 200:
            logger_method = get_task_retry_logger_method(task, logger)
            logger_method(
                f"Unexpected status code {response.status_code}:{response.content}",
                extra={
                    "MESSAGE_ID": "TREASURY_UNSUCCESSFUL_STATUS_CODE",
                    "STATUS_CODE": response.status_code,
                })
            raise task.retry(countdown=get_exponential_request_retry_countdown(task, response))
        else:
            return parse_response_content(response.content)


def parse_response_content(content):
    r = etree.fromstring(content)
    response_tag = r[0][0]
    data = response_tag.find(".//Data", namespaces=response_tag.nsmap)
    if data is not None:
        result = base64.b64decode(data.text)
        return result


def parse_organisations(xml):
    tree = etree.fromstring(xml)
    for record in tree.findall("record"):
        yield {r.tag: r.text for r in record}
