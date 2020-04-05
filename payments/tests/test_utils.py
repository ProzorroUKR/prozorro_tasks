import unittest

from payments.utils import (
    get_payment_params,
    get_item_data,
    check_complaint_status,
    check_complaint_value_amount,
    check_complaint_value_currency,
    ALLOWED_COMPLAINT_PAYMENT_STATUSES,
)

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
