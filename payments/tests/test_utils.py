import unittest
from unittest.mock import patch, MagicMock

from environment_settings import API_TOKEN, API_HOST, API_VERSION, PUBLIC_API_HOST
from payments.utils import (
    get_payment_params,
    get_item_data,
    check_complaint_status,
    check_complaint_value_amount,
    check_complaint_value_currency,
    ALLOWED_COMPLAINT_PAYMENT_STATUSES,
    request_complaint_search,
    get_request_headers,
    get_complaint_search_url,
    request_tender_data,
    get_tender_url,
    request_complaint_data,
    get_complaint_url,
    request_complaint_patch,
)
from tasks_utils.settings import CONNECT_TIMEOUT, READ_TIMEOUT

valid_zoned_complaint_str = [
    "UA-2020-03-17-000090-a.a2-12AD3F12",
    "ua-2020-03-17-000090-a.a2-12ad3f12",
    "Text - UA-2020-03-17-000090-a.a2-12AD3F12",
    "UA-2020-03-17-000090-a.a2-12AD3F12 = text",
]

valid_zoned_complaint_multiple_str = [
    "UA-2020-03-17-000090-a.a112-12AD3F12",
    "ua-2020-03-17-000090-a.a112-12ad3f12",
    "Text - UA-2020-03-17-000090-a.a112-12AD3F12",
    "UA-2020-03-17-000090-a.a112-12AD3F12 = text",
]

valid_zoned_complaint_second_stage_str = [
    "UA-2020-03-17-000090-a.2.a2-12AD3F12",
    "ua-2020-03-17-000090-a.2.a2-12ad3f12",
    "Text - UA-2020-03-17-000090-a.2.a2-12AD3F12",
    "UA-2020-03-17-000090-a.2.a2-12AD3F12 = text",
]

valid_not_zoned_complaint_str = [
    "UA-2020-03-17-000090.2-12AD3F12",
    "ua-2020-03-17-000090.2-12ad3f12",
    "Text - UA-2020-03-17-000090.2-12AD3F12",
    "UA-2020-03-17-000090.2-12AD3F12 = text",
]


class GetPaymentParamsTestCase(unittest.TestCase):
    """
    Test utils.get_payment_params
    """

    def test_valid_zoned_complaint(self):
        for complaint_str in valid_zoned_complaint_str:
            params = get_payment_params(complaint_str)
            self.assertIsNotNone(params)
            self.assertIn("complaint", params)
            self.assertIn("code", params)
            self.assertEqual(
                {
                    "complaint": params["complaint"].lower(),
                    "code": params["code"].lower(),
                },
                {
                    "complaint": "UA-2020-03-17-000090-a.a2".lower(),
                    "code": "12AD3F12".lower(),
                }
            )

    def test_valid_zoned_complaint_multiple(self):
        for complaint_str in valid_zoned_complaint_multiple_str:
            params = get_payment_params(complaint_str)
            self.assertIsNotNone(params)
            self.assertIn("complaint", params)
            self.assertIn("code", params)
            self.assertEqual(
                {
                    "complaint": params["complaint"].lower(),
                    "code": params["code"].lower(),
                },
                {
                    "complaint": "UA-2020-03-17-000090-a.a112".lower(),
                    "code": "12AD3F12".lower(),
                }
            )

    def test_valid_zoned_complaint_second_stage(self):
        for complaint_str in valid_zoned_complaint_second_stage_str:
            params = get_payment_params(complaint_str)
            self.assertIsNotNone(params)
            self.assertIn("complaint", params)
            self.assertIn("code", params)
            self.assertEqual(
                {
                    "complaint": params["complaint"].lower(),
                    "code": params["code"].lower(),
                },
                {
                    "complaint": "UA-2020-03-17-000090-a.2.a2".lower(),
                    "code": "12AD3F12".lower(),
                }
            )

    def test_valid_not_zoned_complaint(self):
        for complaint_str in valid_not_zoned_complaint_str:
            params = get_payment_params(complaint_str)
            self.assertIsNotNone(params)
            self.assertIn("complaint", params)
            self.assertIn("code", params)
            self.assertEqual(
                {
                    "complaint": params["complaint"].lower(),
                    "code": params["code"].lower(),
                },
                {
                    "complaint": "UA-2020-03-17-000090.2".lower(),
                    "code": "12AD3F12".lower(),
                }
            )

    def test_invalid_complaint(self):
        params = get_payment_params("some_str")
        self.assertIsNone(params)


class GetItemDataTestCase(unittest.TestCase):
    """
    Test utils.get_item_data
    """

    def test_item_found(self):
        first_item = {"id": "1", "value": "fail"}
        second_item = {"id": "2", "value": "success"}
        data = {"items": [first_item, second_item]}
        self.assertEqual(
            get_item_data(data, "items", second_item["id"]),
            second_item
        )

    def test_item_not_found(self):
        first_item = {"id": "1", "value": "fail"}
        second_item = {"id": "2", "value": "success"}
        data = {"items": [first_item, second_item]}
        self.assertEqual(
            get_item_data(data, "items", "invalid_id"),
            None
        )

    def test_items_empty(self):
        data = {"items": []}
        self.assertEqual(
            get_item_data(data, "items", "invalid_id"),
            None
        )

    def test_items_not_exists(self):
        data = {}
        self.assertEqual(
            get_item_data(data, "items", "invalid_id"),
            None
        )


class CheckComplaintStatusTestCase(unittest.TestCase):
    """
    Test utils.check_complaint_status
    """

    def test_valid_status(self):
        for status in ALLOWED_COMPLAINT_PAYMENT_STATUSES:
            self.assertTrue(check_complaint_status({"status": status}))

    def test_invalid_status(self):
        self.assertFalse(check_complaint_status({"status": "some_test_invalid_status"}))

    def test_no_status(self):
        self.assertFalse(check_complaint_status({}))



class CheckComplaintValueAmountTestCase(unittest.TestCase):
    """
    Test utils.check_complaint_value_amount
    """

    def test_valid_amount(self):
        self.assertTrue(check_complaint_value_amount(
            {"value": {"amount": 100}},
            {"amount": 100}
        ))

    def test_invalid_amount(self):
        self.assertFalse(check_complaint_value_amount(
            {"value": {"amount": 90}},
            {"amount": 100}
        ))

    def test_no_complaint_amount(self):
        self.assertFalse(check_complaint_value_amount(
            {"value": {}},
            {"amount": 100}
        ))

    def test_no_complaint_value(self):
        self.assertFalse(check_complaint_value_amount(
            {},
            {"amount": 100}
        ))

    def test_no_payment_amount(self):
        self.assertFalse(check_complaint_value_amount(
            {"value": {"amount": 100}},
            {}
        ))

    def test_complaint_amount_float(self):
        self.assertTrue(check_complaint_value_amount(
            {"value": {"amount": 100.0}},
            {"amount": 100}
        ))

    def test_payment_amount_float(self):
        self.assertTrue(check_complaint_value_amount(
            {"value": {"amount": 100}},
            {"amount": 100.0}
        ))

    def test_payment_amount_str(self):
        self.assertTrue(check_complaint_value_amount(
            {"value": {"amount": 100.0}},
            {"amount": "100"}
        ))

    def test_complaint_amount_str(self):
        self.assertTrue(check_complaint_value_amount(
            {"value": {"amount": "100"}},
            {"amount": 100.0}
        ))


class CheckComplaintValueCurrencyTestCase(unittest.TestCase):
    """
    Test utils.check_complaint_value_currency
    """

    def test_valid_currency(self):
        self.assertTrue(check_complaint_value_currency(
            {"value": {"currency": "UAH"}},
            {"currency": "UAH"}
        ))

    def test_invalid_currency(self):
        self.assertFalse(check_complaint_value_currency(
            {"value": {"currency": "USD"}},
            {"currency": "UAH"}
        ))

    def test_no_complaint_currency(self):
        self.assertFalse(check_complaint_value_currency(
            {"value": {}},
            {"currency": "UAH"}
        ))

    def test_no_complaint_value(self):
        self.assertFalse(check_complaint_value_currency(
            {},
            {"currency": "UAH"}
        ))

    def test_no_payment_currency(self):
        self.assertFalse(check_complaint_value_currency(
            {"value": {"currency": "UAH"}},
            {}
        ))


class GetRequestHeadersTestCase(unittest.TestCase):
    """
    Test utils.get_request_headers
    """


class GetComplaintSearchUrlTestCase(unittest.TestCase):
    """
    Test utils.get_complaint_search_url
    """
    def test_get_complaint_search_url(self):
        complaint_pretty_id = "TEST-PRETTY-ID"
        result = get_complaint_search_url(complaint_pretty_id)
        url_pattern = "{host}/api/{version}/complaints/search?complaint_id={complaint_pretty_id}"
        self.assertEqual(result, url_pattern.format(
            host=API_HOST,
            version=API_VERSION,
            complaint_pretty_id=complaint_pretty_id
        ))


class GetComplaintUrlTestCase(unittest.TestCase):
    """
    Test utils.get_complaint_url
    """
    def test_get_complaint_url(self):
        tender_id = "test_tender_id"
        complaint_id = "test_complaint_id"
        result = get_complaint_url(tender_id, None, None, complaint_id)
        url_pattern = "{host}/api/{version}/tenders/{tender_id}/complaints/{complaint_id}"
        self.assertEqual(result, url_pattern.format(
            host=API_HOST,
            version=API_VERSION,
            tender_id=tender_id,
            complaint_id=complaint_id,
        ))

    def test_get_complaint_url_item(self):
        tender_id = "test_tender_id"
        item_type = "test_item_type"
        item_id = "test_item_id"
        complaint_id = "test_complaint_id"
        result = get_complaint_url(tender_id, item_type, item_id, complaint_id)
        url_pattern = "{host}/api/{version}/tenders/{tender_id}/{item_type}/{item_id}/complaints/{complaint_id}"
        self.assertEqual(result, url_pattern.format(
            host=API_HOST,
            version=API_VERSION,
            tender_id=tender_id,
            item_type=item_type,
            item_id=item_id,
            complaint_id=complaint_id,
        ))


class GetTenderUrlTestCase(unittest.TestCase):
    """
    Test utils.get_tender_url
    """
    def test_get_complaint_url(self):
        tender_id = "test_tender_id"
        complaint_id = "test_complaint_id"
        result = get_tender_url(tender_id)
        url_pattern = "{host}/api/{version}/tenders/{tender_id}"
        self.assertEqual(result, url_pattern.format(
            host=PUBLIC_API_HOST,
            version=API_VERSION,
            tender_id=tender_id,
        ))


class RequestComplaintSearchTestCase(unittest.TestCase):
    """
    Test utils.request_complaint_search
    """

    @patch("payments.utils.uuid4", MagicMock())
    @patch("payments.utils.requests")
    def test_request_complaint_search(self, requests):
        complaint_pretty_id = "TEST-PRETTY-ID"

        url = get_complaint_search_url(complaint_pretty_id)
        headers = get_request_headers(authorization=True)
        timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)

        result = request_complaint_search(complaint_pretty_id)

        self.assertEqual(result, requests.get.return_value)

        requests.get.assert_called_once_with(
            url, headers=headers, timeout=timeout, cookies=None
        )

    @patch("payments.utils.requests")
    def test_request_complaint_search_with_optional_args(self, requests):
        complaint_pretty_id = "TEST-PRETTY-ID"
        client_request_id = "test-client-req-id"
        host = "https://test.host"
        cookies = {"test_cookie_name": "test_cookie_value"}

        url = get_complaint_search_url(complaint_pretty_id)
        headers = get_request_headers(client_request_id=client_request_id, authorization=True)
        timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)

        result = request_complaint_search(
            complaint_pretty_id,
            client_request_id=client_request_id,
            cookies=cookies,
        )

        self.assertEqual(result, requests.get.return_value)

        requests.get.assert_called_once_with(
            url, headers=headers, timeout=timeout, cookies=cookies
        )


class RequestTenderDataTestCase(unittest.TestCase):
    """
    Test utils.request_tender_data
    """

    @patch("payments.utils.uuid4", MagicMock())
    @patch("payments.utils.requests")
    def test_request_tender_data(self, requests):
        tender_id = "test_tender_id"

        url = get_tender_url(tender_id)
        headers = get_request_headers(authorization=False)
        timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)

        result = request_tender_data(tender_id)

        self.assertEqual(result, requests.get.return_value)

        requests.get.assert_called_once_with(
            url, headers=headers, timeout=timeout, cookies=None
        )

    @patch("payments.utils.requests")
    def test_request_tender_data_with_optional_args(self, requests):
        tender_id = "test_tender_id"
        client_request_id = "test-client-req-id"
        host = "https://test.host"
        cookies = {"test_cookie_name": "test_cookie_value"}

        url = get_tender_url(tender_id)
        headers = get_request_headers(client_request_id=client_request_id, authorization=False)
        timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)

        result = request_tender_data(
            tender_id,
            client_request_id=client_request_id,
            cookies=cookies,
        )

        self.assertEqual(result, requests.get.return_value)

        requests.get.assert_called_once_with(
            url, headers=headers, timeout=timeout, cookies=cookies
        )


class RequestComplaintDataTestCase(unittest.TestCase):
    """
    Test utils.request_complaint_data
    """

    @patch("payments.utils.uuid4", MagicMock())
    @patch("payments.utils.requests")
    def test_request_complaint_data(self, requests):
        tender_id = "test_tender_id"
        item_type = "test_item_type"
        item_id = "test_item_id"
        complaint_id = "test_complaint_id"

        url = get_complaint_url(tender_id, item_type, item_id, complaint_id)
        headers = get_request_headers(authorization=False)
        timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)

        result = request_complaint_data(
            tender_id, item_type, item_id, complaint_id
        )

        self.assertEqual(result, requests.get.return_value)

        requests.get.assert_called_once_with(
            url, headers=headers, timeout=timeout, cookies=None
        )

    @patch("payments.utils.requests")
    def test_request_complaint_data_with_optional_args(self, requests):
        tender_id = "test_tender_id"
        item_type = "test_item_type"
        item_id = "test_item_id"
        complaint_id = "test_complaint_id"
        client_request_id = "test-client-req-id"
        host = "https://test.host"
        cookies = {"test_cookie_name": "test_cookie_value"}

        url = get_complaint_url(tender_id, item_type, item_id, complaint_id)
        headers = get_request_headers(client_request_id=client_request_id, authorization=False)
        timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)

        result = request_complaint_data(
            tender_id, item_type, item_id, complaint_id,
            client_request_id=client_request_id,
            cookies=cookies,
        )

        self.assertEqual(result, requests.get.return_value)

        requests.get.assert_called_once_with(
            url, headers=headers, timeout=timeout, cookies=cookies
        )



class RequestComplaintPatchTestCase(unittest.TestCase):
    """
    Test utils.request_complaint_patch
    """

    @patch("payments.utils.uuid4", MagicMock())
    @patch("payments.utils.requests")
    def test_request_complaint_patch(self, requests):
        tender_id = "test_tender_id"
        item_type = "test_item_type"
        item_id = "test_item_id"
        complaint_id = "test_complaint_id"
        data = {"test_data_field": "test_data_value"}

        url = get_complaint_url(tender_id, item_type, item_id, complaint_id)
        json = {"data": data}
        headers = get_request_headers(authorization=True)
        timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)

        result = request_complaint_patch(
            tender_id, item_type, item_id, complaint_id, data
        )

        self.assertEqual(result, requests.patch.return_value)

        requests.patch.assert_called_once_with(
            url, json=json, headers=headers, timeout=timeout, cookies=None
        )

    @patch("payments.utils.requests")
    def test_request_complaint_patch_with_optional_args(self, requests):
        tender_id = "test_tender_id"
        item_type = "test_item_type"
        item_id = "test_item_id"
        complaint_id = "test_complaint_id"
        data = {"test_data_field": "test_data_value"}
        client_request_id = "test-client-req-id"
        host = "https://test.host"
        cookies = {"test_cookie_name": "test_cookie_value"}

        url = get_complaint_url(tender_id, item_type, item_id, complaint_id)
        json = {"data": data}
        headers = get_request_headers(client_request_id=client_request_id, authorization=True)
        timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)

        result = request_complaint_patch(
            tender_id, item_type, item_id, complaint_id, data,
            client_request_id=client_request_id,
            cookies=cookies,
        )

        self.assertEqual(result, requests.patch.return_value)

        requests.patch.assert_called_once_with(
            url, json=json, headers=headers, timeout=timeout, cookies=cookies
        )
