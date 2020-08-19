import unittest
from datetime import datetime, timedelta
from json import JSONDecodeError
from unittest.mock import patch, MagicMock

from environment_settings import API_HOST, API_VERSION, PUBLIC_API_HOST
from payments.utils import (
    get_payment_params,
    get_item_data,
    check_complaint_status,
    check_complaint_value_amount,
    check_complaint_value_currency,
    ALLOWED_COMPLAINT_PAYMENT_STATUSES,
    request_cdb_complaint_search,
    get_cdb_request_headers,
    get_cdb_complaint_search_url,
    request_cdb_tender_data,
    get_cdb_tender_url,
    request_cdb_complaint_data,
    get_cdb_complaint_url,
    request_cdb_complaint_patch,
    get_payments_registry,
    get_payments_registry_fake,
    dumps_payments_registry_fake,
    store_payments_registry_fake,
    put_payments_registry_fake_data,
    get_payments_registry_fake_data,
)
from tasks_utils.settings import CONNECT_TIMEOUT, READ_TIMEOUT


VALID_ZONED_COMPLAINT_STR = "UA-2020-03-17-000090-a.c2-12ABCDEF"
VALID_ZONED_COMPLAINT_MULTIPLE_STR = "UA-2020-03-17-000090-a.c112-12ABCDEF"
VALID_ZONED_COMPLAINT_SECOND_STAGE_STR = "UA-2020-03-17-000090-a.2.c2-12ABCDEF"
VALID_NOT_ZONED_COMPLAINT_STR = "UA-2020-03-17-000090.2-12ABCDEF"


def generate_complaint_test_data(complaint_str):
    return [
        (complaint_str, "default"),
        (complaint_str.lower(), "lowercase"),
        ("Text {} text".format(complaint_str), "additional text"),
        (" ".join(complaint_str), "replace whitespaces"),
        (complaint_str.replace("c", "с"), "replace cyrillic to latin - c"),
        (complaint_str.replace("a", "а"), "replace cyrillic to latin - a"),
        (complaint_str.replace("e", "е"), "replace cyrillic to latin - e"),
        (complaint_str.replace("C", "С"), "replace cyrillic to latin - C"),
        (complaint_str.replace("A", "А"), "replace cyrillic to latin - A"),
        (complaint_str.replace("E", "Е"), "replace cyrillic to latin - E"),
        (complaint_str.replace("B", "В"), "replace cyrillic to latin - B"),
        (complaint_str.replace("-", "--"), "replace double -- with -"),
        (complaint_str.replace("-", "—"), "replace — with -"),
        (complaint_str.replace(".", ","), "replace , with ."),
        (complaint_str.replace("-", "!@#$"), "replace any non alphanumeric with -"),
        (complaint_str.replace("1", "l"), "replace latin l with 1"),
        (complaint_str.replace("1", "I"), "replace latin I with 1"),
        (complaint_str.replace("1", "І"), "replace cyrillic І with 1"),
        (complaint_str.replace("1", "i"), "replace latin i with 1"),
        (complaint_str.replace("1", "і"), "replace cyrillic  with 1"),
        (complaint_str.replace("0", "O"), "replace latin O with 0"),
        (complaint_str.replace("0", "О"), "replace cyrillic О with 0"),
    ]


class GetPaymentParamsTestCase(unittest.TestCase):
    """
    Test utils.get_payment_params
    """

    def test_valid_zoned_complaint(self):
        for complaint_str, info in generate_complaint_test_data(VALID_ZONED_COMPLAINT_STR):
            params = get_payment_params(complaint_str)
            self.assertIsNotNone(params, complaint_str)
            self.assertIn("complaint", params, complaint_str)
            self.assertIn("code", params, complaint_str)
            self.assertEqual(
                {
                    "complaint": params["complaint"].lower(),
                    "code": params["code"].lower(),
                },
                {
                    "complaint": "UA-2020-03-17-000090-a.c2".lower(),
                    "code": "12ABCDEF".lower(),
                },
                "Failed: {}, {}".format(info, complaint_str)
            )

    def test_valid_zoned_complaint_multiple(self):
        for complaint_str, info in generate_complaint_test_data(VALID_ZONED_COMPLAINT_MULTIPLE_STR):
            params = get_payment_params(complaint_str)
            self.assertIsNotNone(params, complaint_str)
            self.assertIn("complaint", params, complaint_str)
            self.assertIn("code", params, complaint_str)
            self.assertEqual(
                {
                    "complaint": params["complaint"].lower(),
                    "code": params["code"].lower(),
                },
                {
                    "complaint": "UA-2020-03-17-000090-a.c112".lower(),
                    "code": "12ABCDEF".lower(),
                },
                "Failed: {}, {}".format(info, complaint_str)
            )

    def test_valid_zoned_complaint_second_stage(self):
        for complaint_str, info in generate_complaint_test_data(VALID_ZONED_COMPLAINT_SECOND_STAGE_STR):
            params = get_payment_params(complaint_str)
            self.assertIsNotNone(params, complaint_str)
            self.assertIn("complaint", params, complaint_str)
            self.assertIn("code", params, complaint_str)
            self.assertEqual(
                {
                    "complaint": params["complaint"].lower(),
                    "code": params["code"].lower(),
                },
                {
                    "complaint": "UA-2020-03-17-000090-a.2.c2".lower(),
                    "code": "12ABCDEF".lower(),
                },
                "Failed: {}, {}".format(info, complaint_str)
            )

    def test_valid_not_zoned_complaint(self):
        for complaint_str, info in generate_complaint_test_data(VALID_NOT_ZONED_COMPLAINT_STR):
            params = get_payment_params(complaint_str)
            self.assertIsNotNone(params, complaint_str)
            self.assertIn("complaint", params, complaint_str)
            self.assertIn("code", params, complaint_str)
            self.assertEqual(
                {
                    "complaint": params["complaint"].lower(),
                    "code": params["code"].lower(),
                },
                {
                    "complaint": "UA-2020-03-17-000090.2".lower(),
                    "code": "12ABCDEF".lower(),
                },
                "Failed: {}, {}".format(info, complaint_str)
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
        result = get_cdb_complaint_search_url(complaint_pretty_id)
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
        result = get_cdb_complaint_url(tender_id, None, None, complaint_id)
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
        result = get_cdb_complaint_url(tender_id, item_type, item_id, complaint_id)
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
        result = get_cdb_tender_url(tender_id)
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

        url = get_cdb_complaint_search_url(complaint_pretty_id)
        headers = get_cdb_request_headers(authorization=True)
        timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)

        result = request_cdb_complaint_search(complaint_pretty_id)

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

        url = get_cdb_complaint_search_url(complaint_pretty_id)
        headers = get_cdb_request_headers(client_request_id=client_request_id, authorization=True)
        timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)

        result = request_cdb_complaint_search(
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

        url = get_cdb_tender_url(tender_id)
        headers = get_cdb_request_headers(authorization=False)
        timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)

        result = request_cdb_tender_data(tender_id)

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

        url = get_cdb_tender_url(tender_id)
        headers = get_cdb_request_headers(client_request_id=client_request_id, authorization=False)
        timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)

        result = request_cdb_tender_data(
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

        url = get_cdb_complaint_url(tender_id, item_type, item_id, complaint_id)
        headers = get_cdb_request_headers(authorization=False)
        timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)

        result = request_cdb_complaint_data(
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

        url = get_cdb_complaint_url(tender_id, item_type, item_id, complaint_id)
        headers = get_cdb_request_headers(client_request_id=client_request_id, authorization=False)
        timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)

        result = request_cdb_complaint_data(
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

        url = get_cdb_complaint_url(tender_id, item_type, item_id, complaint_id)
        json = {"data": data}
        headers = get_cdb_request_headers(authorization=True)
        timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)

        result = request_cdb_complaint_patch(
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

        url = get_cdb_complaint_url(tender_id, item_type, item_id, complaint_id)
        json = {"data": data}
        headers = get_cdb_request_headers(client_request_id=client_request_id, authorization=True)
        timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)

        result = request_cdb_complaint_patch(
            tender_id, item_type, item_id, complaint_id, data,
            client_request_id=client_request_id,
            cookies=cookies,
        )

        self.assertEqual(result, requests.patch.return_value)

        requests.patch.assert_called_once_with(
            url, json=json, headers=headers, timeout=timeout, cookies=cookies
        )


class GetPaymentsRegistryTestCase(unittest.TestCase):

    @patch("payments.utils.LIQPAY_INTEGRATION_API_HOST", "http://test.example.com")
    @patch("payments.utils.LIQPAY_INTEGRATION_API_PATH", "test/path")
    @patch("payments.utils.LIQPAY_PROZORRO_ACCOUNT", "test")
    @patch("payments.utils.LIQPAY_API_PROXIES", {"http": "http://proxy.example.com"})
    @patch("payments.utils.requests")
    def test_get_payments_registry(self, requests):
        date_from = MagicMock()
        date_from.timestamp.return_value = 1
        date_to = MagicMock()
        date_to.timestamp.return_value = 2

        result = get_payments_registry(date_from, date_to)

        requests.post.assert_called_once_with(
            "http://test.example.com/test/path",
            proxies={"http": "http://proxy.example.com"},
            json={
                "account": "test",
                "date_from": 1 * 1000,
                "date_to": 2 * 1000,
            }
        )
        requests.post.return_value.json.assert_called_once_with()
        self.assertEqual(result, requests.post.return_value.json.return_value)

    @patch("payments.utils.LIQPAY_PROZORRO_ACCOUNT", "test")
    @patch("payments.utils.requests")
    def test_get_payments_registry_request_fail(self, requests):
        date_from = MagicMock()
        date_to = MagicMock()
        requests.post.side_effect = Exception

        result = get_payments_registry(date_from, date_to)

        self.assertEqual(requests.post.call_count, 1)
        self.assertIsNone(result)

    @patch("payments.utils.LIQPAY_PROZORRO_ACCOUNT", None)
    @patch("payments.utils.requests")
    def test_get_payments_registry_with_no_account(self, requests):
        date_from = MagicMock()
        date_to = MagicMock()

        result = get_payments_registry(date_from, date_to)

        self.assertEqual(requests.post.call_count, 0)
        self.assertIsNone(result)


class GetPaymentsRegistryFakeTestCase(unittest.TestCase):

    @patch("payments.utils.shelve")
    def test_get_payments_registry_fake(self, shelve):
        date_from = datetime.now() - timedelta(days=1)
        date_to = datetime.now() + timedelta(days=1)
        shelve.open.return_value.__enter__.return_value = {
            "registry": [
                {
                    "date_oper": datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                }
            ]
        }

        result = get_payments_registry_fake(date_from, date_to)

        shelve.open.assert_called_once_with('payments.db')
        self.assertEqual(result, {
            "status": "success",
            "messages": shelve.open.return_value.__enter__.return_value["registry"]
        })

    @patch("payments.utils.shelve")
    def test_get_payments_registry_fake_invalid_date_oper_format(self, shelve):
        date_from = datetime.now() - timedelta(days=1)
        date_to = datetime.now() + timedelta(days=1)
        shelve.open.return_value.__enter__.return_value = {
            "registry": [
                {
                    "date_oper": "test"
                }
            ]
        }

        result = get_payments_registry_fake(date_from, date_to)

        shelve.open.assert_called_once_with('payments.db')
        self.assertEqual(result, {
            "status": "success",
            "messages": []
        })

    @patch("payments.utils.shelve")
    def test_get_payments_registry_fake_not_in_range(self, shelve):
        date_from = datetime.now() - timedelta(days=2)
        date_to = datetime.now() - timedelta(days=1)
        shelve.open.return_value.__enter__.return_value = {
            "registry": [
                {
                    "date_oper": datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                }
            ]
        }

        result = get_payments_registry_fake(date_from, date_to)

        shelve.open.assert_called_once_with('payments.db')
        self.assertEqual(result, {
            "status": "success",
            "messages": []
        })

    @patch("payments.utils.shelve")
    def test_get_payments_registry_fake_shelve_registry_empty_list(self, shelve):
        date_from = datetime.now() - timedelta(days=2)
        date_to = datetime.now() - timedelta(days=1)
        shelve.open.return_value.__enter__.return_value = {"registry": []}

        result = get_payments_registry_fake(date_from, date_to)

        shelve.open.assert_called_once_with('payments.db')
        self.assertEqual(result, {
            "status": "success",
            "messages": []
        })

    @patch("payments.utils.shelve")
    def test_get_payments_registry_fake_shelve_not_initiated(self, shelve):
        date_from = datetime.now() - timedelta(days=2)
        date_to = datetime.now() - timedelta(days=1)
        shelve.open.return_value.__enter__.return_value = {}

        result = get_payments_registry_fake(date_from, date_to)

        shelve.open.assert_called_once_with('payments.db')
        self.assertIsNone(result)

    @patch("payments.utils.shelve")
    def test_get_payments_registry_fake_shelve_registry_unset(self, shelve):
        date_from = datetime.now() - timedelta(days=2)
        date_to = datetime.now() - timedelta(days=1)
        shelve.open.return_value.__enter__.return_value = {"registry": None}

        result = get_payments_registry_fake(date_from, date_to)

        shelve.open.assert_called_once_with('payments.db')
        self.assertIsNone(result)


class DumpsPaymentsRegistryFakeTestCase(unittest.TestCase):

    @patch("payments.utils.json")
    @patch("payments.utils.shelve")
    def test_dumps_payments_registry_fake(self, shelve, json):
        dumps_payments_registry_fake()

        shelve.open.assert_called_once_with('payments.db')
        json.dumps.assert_called_once_with(
            shelve.open.return_value.__enter__.return_value.get.return_value,
            indent=4,
            ensure_ascii=False
        )
        shelve.open.return_value.__enter__.return_value.get.assert_called_once_with("registry", None)


class StorePaymentsRegistryFakeTestCase(unittest.TestCase):

    @patch("payments.utils.json")
    @patch("payments.utils.shelve")
    def test_store_payments_registry_fake(self, shelve, json):
        text = "test"
        shelve.open.return_value.__enter__.return_value = dict()

        store_payments_registry_fake(text)

        json.loads.assert_called_once_with(text)
        shelve.open.assert_called_once_with('payments.db')
        self.assertEqual(
            shelve.open.return_value.__enter__.return_value['registry'],
            json.loads.return_value
        )

    @patch("payments.utils.json")
    @patch("payments.utils.shelve")
    def test_store_payments_registry_fake_json_decode_error(self, shelve, json):
        text = "test"
        shelve.open.return_value.__enter__.return_value = dict()
        json.loads.side_effect = JSONDecodeError("test", "test", 1)

        store_payments_registry_fake(text)

        self.assertEqual(shelve.open.call_count, 0)
        self.assertEqual(
            shelve.open.return_value.__enter__.return_value,
            dict()
        )

    @patch("payments.utils.json")
    @patch("payments.utils.shelve")
    def test_store_payments_registry_fake_none(self, shelve, json):
        text = None
        shelve.open.return_value.__enter__.return_value = dict()

        store_payments_registry_fake(text)

        shelve.open.assert_called_once_with('payments.db')
        self.assertEqual(
            shelve.open.return_value.__enter__.return_value['registry'],
            None
        )


class PutPaymentsRegistryFakeDataTestCase(unittest.TestCase):

    @patch("payments.utils.shelve")
    def test_put_payments_registry_fake_data(self, shelve):
        data = "test"
        shelve.open.return_value.__enter__.return_value = dict()

        put_payments_registry_fake_data(data)

        shelve.open.assert_called_once_with('payments.db')
        self.assertEqual(
            shelve.open.return_value.__enter__.return_value['registry'],
            data
        )

    @patch("payments.utils.shelve")
    def test_put_payments_registry_fake_data_os_error(self, shelve):
        data = "test"
        shelve.open.side_effect = OSError
        shelve.open.return_value.__enter__.return_value = None

        put_payments_registry_fake_data(data)

        shelve.open.assert_called_once_with('payments.db')
        self.assertEqual(
            shelve.open.return_value.__enter__.return_value,
            None
        )



class GetPaymentsRegistryFakeDataTestCase(unittest.TestCase):

    @patch("payments.utils.shelve")
    def test_get_payments_registry_fake_data(self, shelve):
        data = "test"
        shelve.open.return_value.__enter__.return_value = {'registry': data}

        result = get_payments_registry_fake_data()

        shelve.open.assert_called_once_with('payments.db')
        self.assertEqual(
            shelve.open.return_value.__enter__.return_value['registry'],
            data
        )
        self.assertEqual(result, data)

    @patch("payments.utils.shelve")
    def test_get_payments_registry_fake_data_os_error(self, shelve):
        data = "test"
        shelve.open.side_effect = OSError
        shelve.open.return_value.__enter__.return_value = {'registry': data}

        result = get_payments_registry_fake_data()

        shelve.open.assert_called_once_with('payments.db')
        self.assertEqual(
            shelve.open.return_value.__enter__.return_value,
            {'registry': data}
        )
        self.assertEqual(result, None)
