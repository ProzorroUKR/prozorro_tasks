from environment_settings import TREASURY_PASSWORD, TREASURY_USER, TREASURY_WSDL_URL
from tasks_utils.settings import CONNECT_TIMEOUT, READ_TIMEOUT
from treasury.api_requests import (
    parse_request_response, prepare_request_data, send_request,
    prepare_get_response_data, parse_response_content, get_request_response,
    parse_organisations, get_wsdl_client
)
from requests.exceptions import ConnectTimeout, SSLError
from zeep import Client
from unittest.mock import patch, Mock
import unittest
import base64


class RetryExc(Exception):
    def __init__(self, **_):
        pass


class HelpersTestCase(unittest.TestCase):

    @patch("treasury.api_requests.Client")
    def test_wdsl_client_error(self, client_mock):
        client_mock.side_effect = ConnectTimeout()
        task = Mock(retry=RetryExc)
        with patch("treasury.api_requests.get_exponential_request_retry_countdown", Mock()):
            with self.assertRaises(RetryExc):
                get_wsdl_client(task)


@patch(
    "treasury.api_requests.Client",
    lambda _, **kwargs: Client("file://./treasury/tests/fixtures/wdsl.xml")  # use the local copy
)
class RequestTestCase(unittest.TestCase):

    def test_prepare_request(self):
        task = Mock()
        message_id = 13
        method_name = "TestMe"
        xml = b"<hello>World</hello>"
        sign = b"<<sign>>"
        result = prepare_request_data(task, xml, sign=sign, message_id=message_id, method_name=method_name)
        data = base64.b64encode(xml).decode()
        request = '<soap-env:Envelope xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/"><soap-env:Body>'\
                  '<ns0:SendRequest xmlns:ns0="https://www.unity-bars.com/ws"><ns0:request>' \
                  f'<ns0:UserLogin>{TREASURY_USER}</ns0:UserLogin>' \
                  f'<ns0:UserPassword>{TREASURY_PASSWORD}</ns0:UserPassword>' \
                  f'<ns0:MessageId>{message_id}</ns0:MessageId><ns0:MethodName>{method_name}</ns0:MethodName>' \
                  f'<ns0:Data>{data}</ns0:Data><ns0:DataSign>{base64.b64encode(sign).decode()}</ns0:DataSign>' \
                  f'</ns0:request></ns0:SendRequest>'\
                  '</soap-env:Body></soap-env:Envelope>'
        self.assertEqual(result, request.encode())

    def test_parse_response_xml(self):
        with open("treasury/tests/fixtures/send_request_response.xml", "rb") as f:
            response = f.read()
        result = parse_request_response(response)
        self.assertEqual(result, (0, None))

    def test_parse_response_error_code(self):
        response = b"<xml><Body><Response>" \
                   b"<ResultCode>101</ResultCode><ResultMessage>Non-unique</ResultMessage>" \
                   b"</Response></Body></xml>"
        result = parse_request_response(response)
        self.assertEqual(result, (101, "Non-unique"))

    def test_parse_response_non_int_code(self):
        response = b"<xml><Body><Response>" \
                   b"<ResultCode>Beep</ResultCode><ResultMessage/>" \
                   b"</Response></Body></xml>"
        result = parse_request_response(response)
        self.assertEqual(result, ("Beep", None))

    def test_send_request(self):
        task = Mock()
        xml = b"<tag>Hi</tag>"
        sign = b"<sign>"
        message_id = 123
        method_name = "GetRef"
        with open("treasury/tests/fixtures/send_request_response.xml", "rb") as f:
            session_mock = Mock(post=Mock(return_value=Mock(status_code=200, content=f.read())))

        with patch("treasury.api_requests.prepare_request_data") as prepare_data_mock:
            prepare_data_mock.return_value = "<request></request>"
            with patch("treasury.api_requests.Session", lambda: session_mock):
                result = send_request(task, xml, sign=sign, message_id=message_id, method_name=method_name)

        prepare_data_mock.assert_called_once_with(
            task, xml, sign, message_id, method_name
        )
        session_mock.post.assert_called_once_with(
            TREASURY_WSDL_URL,
            data='<request></request>',
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={'content-type': 'text/xml'},
        )
        self.assertEqual(result, (0, None))

    def test_send_request_exception(self):
        task = Mock(retry=RetryExc)
        session_mock = Mock(post=Mock(side_effect=SSLError("Unsafe bla bla")))
        with patch("treasury.api_requests.Session", lambda: session_mock):
            with patch("treasury.api_requests.get_exponential_request_retry_countdown", Mock()):
                with self.assertRaises(RetryExc):
                    send_request(task, b"", sign=b"", message_id=1, method_name="GetRef")

    def test_send_request_error(self):
        task = Mock(retry=RetryExc)
        task.request.retries = 0

        session_mock = Mock(post=Mock(return_value=Mock(status_code=500, content=b"Internal error")))
        with patch("treasury.api_requests.Session", lambda: session_mock):
            with self.assertRaises(RetryExc):
                send_request(task, b"", sign=b"", message_id=1, method_name="GetRef")

    def test_send_request_unsuccessful_code(self):
        task = Mock(retry=RetryExc)
        task.request.retries = 0

        session_mock = Mock(post=Mock(return_value=Mock(status_code=200, content=b"<spam></spam>")))
        with patch("treasury.api_requests.TREASURY_SKIP_REQUEST_VERIFY", True):
            with patch("treasury.api_requests.Session", lambda: session_mock):
                with patch("treasury.api_requests.parse_request_response",
                           lambda _: (100, "Duplicate msg_id")):   # this will cause retry, should it?
                    with self.assertRaises(RetryExc):
                        send_request(task, b"", sign=b"", message_id=1, method_name="GetRef")
        self.assertIs(session_mock.verify, False, "TREASURY_SKIP_REQUEST_VERIFY is True")


@patch(
    "treasury.api_requests.Client",
    lambda _, **kwargs: Client("file://./treasury/tests/fixtures/wdsl.xml")
)
class ResponseTestCase(unittest.TestCase):

    def test_prepare_request(self):
        task = Mock()
        message_id = 131313
        result = prepare_get_response_data(task, message_id)
        self.assertEqual(
            result,
            '<soap-env:Envelope xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/"><soap-env:Body>'
            '<ns0:GetResponse xmlns:ns0="https://www.unity-bars.com/ws">'
            f'<ns0:request><ns0:UserLogin>{TREASURY_USER}</ns0:UserLogin>'
            f'<ns0:UserPassword>{TREASURY_PASSWORD}</ns0:UserPassword>'
            f'<ns0:MessageId>{message_id}</ns0:MessageId>'
            '</ns0:request></ns0:GetResponse></soap-env:Body></soap-env:Envelope>'.encode()
        )

    def test_parse_response_content_empty(self):
        with open("treasury/tests/fixtures/get_response_empty.xml", "rb") as f:
            response = f.read()
        result = parse_response_content(response)
        self.assertEqual(result, None)

    def test_parse_response_content(self):
        with open("treasury/tests/fixtures/get_response_org_list.xml", "rb") as f:
            response = f.read()
        result = parse_response_content(response)

        self.assertTrue(
            result.startswith(
                b'<?xml version="1.0" encoding="windows-1251"?>'
                b'<root ref="sngl_reg_orgs" rec_count="71030" date=""> <record'
            )
        )

        # and test parse_organisations
        records = list(parse_organisations(result))
        self.assertEqual(len(records), 2374)
        self.assertEqual(
            records[0],
            {
                'status_id': '2', 'unit_name': '-', 'code_area': '26', 'budget_type': '1',
                'budget_name': 'Державний бюджет', 'edrpou_code': '5417986', 'parent_edrpou': '21195',
                'parent_name': 'Центральне правління Українського Товариства сліпих', 'kvk_code': '250',
                'long_name': 'Підприємство об"єднання громадян '
                             '"Київське учбово - виробниче підприємство №4 Українського товариства сліпих"',
                'short_name': 'ПОГ "Київське УВП №4 УТОС"', 'zip_code': '2160', 'address': 'м.Київ, вул. Фанерна, 4',
                'phone_code': '044', 'dku_code': '2604', 'dku_name': 'УДКСУ у Дніпровському районі', 'dpi_code': '53',
                'dpi_name': 'ДПI У ДНIПРОВСЬКОМУ РАЙОНI ГУ ДФС У М.КИЄВI', 'upd_date': '2018-05-23T10:27:24'
            }
        )

    def test_get_request_response(self):
        message_id = "947b248c181049868602f0f50285f464"
        with open("treasury/tests/fixtures/get_response_org_list.xml", "rb") as f:
            raw_response = f.read()
            session_mock = Mock(post=Mock(return_value=Mock(status_code=200, content=raw_response)))
        task = Mock()

        with patch("treasury.api_requests.parse_response_content", Mock(return_value=3)) as parse_res_mock:
            with patch("treasury.api_requests.prepare_get_response_data") as prepare_data_mock:
                prepare_data_mock.return_value = "<req_res></req_res>"
                with patch("treasury.api_requests.Session", lambda: session_mock):
                    result = get_request_response(task, message_id)

        prepare_data_mock.assert_called_once_with(task, message_id)
        session_mock.post.assert_called_once_with(
            TREASURY_WSDL_URL,
            data=prepare_data_mock.return_value,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={'content-type': 'text/xml'},
        )
        parse_res_mock.assert_called_once_with(raw_response)
        self.assertEqual(result, 3)

    def test_get_response_exception(self):
        task = Mock(retry=RetryExc)
        session_mock = Mock(post=Mock(side_effect=SSLError("Unsafe bla bla")))
        with patch("treasury.api_requests.Session", lambda: session_mock):
            with patch("treasury.api_requests.get_exponential_request_retry_countdown", Mock()):
                with self.assertRaises(RetryExc):
                        get_request_response(task, 1)

    def test_get_response_error(self):
        task = Mock(retry=RetryExc)
        task.request.retries = 0

        session_mock = Mock(post=Mock(return_value=Mock(status_code=500, content=b"Internal error")))
        self.assertIsNot(session_mock.verify, False, "TREASURY_SKIP_REQUEST_VERIFY is True")
        with patch("treasury.api_requests.TREASURY_SKIP_REQUEST_VERIFY", True):
            with patch("treasury.api_requests.Session", lambda: session_mock):
                with self.assertRaises(RetryExc):
                    get_request_response(task, 1)
        self.assertIs(session_mock.verify, False, "TREASURY_SKIP_REQUEST_VERIFY is True")
