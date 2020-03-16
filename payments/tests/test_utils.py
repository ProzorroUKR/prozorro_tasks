import unittest

from payments.settings import (
    TENDER_COMPLAINT_TYPE, QUALIFICATION_COMPLAINT_TYPE, AWARD_COMPLAINT_TYPE,
    CANCELLATION_COMPLAINT_TYPE,
    ALLOWED_COMPLAINT_PAYMENT_STATUSES,
)
from payments.utils import (
    get_complaint_params, get_complaint_type, get_item_data, check_complaint_status,
    check_complaint_value_amount,
    check_complaint_value_currency,
)

valid_tender_complaint_str = [
    "/tenders/6be521090fa444c881e27af026c04e8a/complaints/3a0cc410ab374e2d8a9361dd59436c76",
    "/tenders/6be521090fa444c881e27af026c04e8a/complaints/3a0cc410ab374e2d8a9361dd59436c76/",
    "/tenders/6be521090fa444c881e27af026c04e8a/complaints/3a0cc410ab374e2d8a9361dd59436c76/ ",
    "/tenders/6be521090fa444c881e27af026c04e8a/complaints/3a0cc410ab374e2d8a9361dd59436c76/ ",
    "Text - /tenders/6be521090fa444c881e27af026c04e8a/complaints/3a0cc410ab374e2d8a9361dd59436c76",
    "/tenders/6be521090fa444c881e27af026c04e8a/complaints/3a0cc410ab374e2d8a9361dd59436c76 - text",
    " / tenders / 6be521090fa444c881e27af026c04e8a / complaints / 3a0cc410ab374e2d8a9361dd59436c76",
    " /tenders /6be521090fa444c881e27af026c04e8a /complaints /3a0cc410ab374e2d8a9361dd59436c76",
    " / tenders/ 6be521090fa444c881e27af026c04e8a/ complaints/ 3a0cc410ab374e2d8a9361dd59436c76",
    "Text - / tenders / 6be521090fa444c881e27af026c04e8a / complaints / 3a0cc410ab374e2d8a9361dd59436c76",
    " / tenders / 6be521090fa444c881e27af026c04e8a / complaints / 3a0cc410ab374e2d8a9361dd59436c76 - text",
]

valid_qualification_complaint_str = [
    "/tenders/6be521090fa444c881e27af026c04e8a/qualifications/6be521090fa444c881e27af026c04e8a/complaints/3a0cc410ab374e2d8a9361dd59436c76",
    "/tenders/6be521090fa444c881e27af026c04e8a/qualifications/6be521090fa444c881e27af026c04e8a/complaints/3a0cc410ab374e2d8a9361dd59436c76/",
    "/tenders/6be521090fa444c881e27af026c04e8a/qualifications/6be521090fa444c881e27af026c04e8a/complaints/3a0cc410ab374e2d8a9361dd59436c76/ ",
    "/tenders/6be521090fa444c881e27af026c04e8a/qualifications/6be521090fa444c881e27af026c04e8a/complaints/3a0cc410ab374e2d8a9361dd59436c76/ ",
    "Text - /tenders/6be521090fa444c881e27af026c04e8a/qualifications/6be521090fa444c881e27af026c04e8a/complaints/3a0cc410ab374e2d8a9361dd59436c76",
    "/tenders/6be521090fa444c881e27af026c04e8a/qualifications/6be521090fa444c881e27af026c04e8a/complaints/3a0cc410ab374e2d8a9361dd59436c76 - text",
    " / tenders / 6be521090fa444c881e27af026c04e8a / qualifications / 6be521090fa444c881e27af026c04e8a / complaints / 3a0cc410ab374e2d8a9361dd59436c76",
    " /tenders /6be521090fa444c881e27af026c04e8a /qualifications /6be521090fa444c881e27af026c04e8a /complaints /3a0cc410ab374e2d8a9361dd59436c76",
    " / tenders/ 6be521090fa444c881e27af026c04e8a/ qualifications/ 6be521090fa444c881e27af026c04e8a/ complaints/ 3a0cc410ab374e2d8a9361dd59436c76",
    "Text - / tenders / 6be521090fa444c881e27af026c04e8a / qualifications / 6be521090fa444c881e27af026c04e8a / complaints / 3a0cc410ab374e2d8a9361dd59436c76",
    " / tenders / 6be521090fa444c881e27af026c04e8a / qualifications / 6be521090fa444c881e27af026c04e8a / complaints / 3a0cc410ab374e2d8a9361dd59436c76 - text",
]

valid_award_complaint_str = [
    "/tenders/6be521090fa444c881e27af026c04e8a/awards/6be521090fa444c881e27af026c04e8a/complaints/3a0cc410ab374e2d8a9361dd59436c76",
    "/tenders/6be521090fa444c881e27af026c04e8a/awards/6be521090fa444c881e27af026c04e8a/complaints/3a0cc410ab374e2d8a9361dd59436c76/",
    "/tenders/6be521090fa444c881e27af026c04e8a/awards/6be521090fa444c881e27af026c04e8a/complaints/3a0cc410ab374e2d8a9361dd59436c76/ ",
    "/tenders/6be521090fa444c881e27af026c04e8a/awards/6be521090fa444c881e27af026c04e8a/complaints/3a0cc410ab374e2d8a9361dd59436c76/ ",
    "Text - /tenders/6be521090fa444c881e27af026c04e8a/awards/6be521090fa444c881e27af026c04e8a/complaints/3a0cc410ab374e2d8a9361dd59436c76",
    "/tenders/6be521090fa444c881e27af026c04e8a/awards/6be521090fa444c881e27af026c04e8a/complaints/3a0cc410ab374e2d8a9361dd59436c76 - text",
    " / tenders / 6be521090fa444c881e27af026c04e8a / awards / 6be521090fa444c881e27af026c04e8a / complaints / 3a0cc410ab374e2d8a9361dd59436c76",
    " /tenders /6be521090fa444c881e27af026c04e8a /awards /6be521090fa444c881e27af026c04e8a /complaints /3a0cc410ab374e2d8a9361dd59436c76",
    " / tenders/ 6be521090fa444c881e27af026c04e8a/ awards/ 6be521090fa444c881e27af026c04e8a/ complaints/ 3a0cc410ab374e2d8a9361dd59436c76",
    "Text - / tenders / 6be521090fa444c881e27af026c04e8a / awards / 6be521090fa444c881e27af026c04e8a / complaints / 3a0cc410ab374e2d8a9361dd59436c76",
    " / tenders / 6be521090fa444c881e27af026c04e8a / awards / 6be521090fa444c881e27af026c04e8a / complaints / 3a0cc410ab374e2d8a9361dd59436c76 - text",
]

valid_cancellation_complaint_str = [
    "/tenders/6be521090fa444c881e27af026c04e8a/cancellations/6be521090fa444c881e27af026c04e8a/complaints/3a0cc410ab374e2d8a9361dd59436c76",
    "/tenders/6be521090fa444c881e27af026c04e8a/cancellations/6be521090fa444c881e27af026c04e8a/complaints/3a0cc410ab374e2d8a9361dd59436c76/",
    "/tenders/6be521090fa444c881e27af026c04e8a/cancellations/6be521090fa444c881e27af026c04e8a/complaints/3a0cc410ab374e2d8a9361dd59436c76/ ",
    "/tenders/6be521090fa444c881e27af026c04e8a/cancellations/6be521090fa444c881e27af026c04e8a/complaints/3a0cc410ab374e2d8a9361dd59436c76/ ",
    "Text - /tenders/6be521090fa444c881e27af026c04e8a/cancellations/6be521090fa444c881e27af026c04e8a/complaints/3a0cc410ab374e2d8a9361dd59436c76",
    "/tenders/6be521090fa444c881e27af026c04e8a/cancellations/6be521090fa444c881e27af026c04e8a/complaints/3a0cc410ab374e2d8a9361dd59436c76 - text",
    " / tenders / 6be521090fa444c881e27af026c04e8a / cancellations / 6be521090fa444c881e27af026c04e8a / complaints / 3a0cc410ab374e2d8a9361dd59436c76",
    " /tenders /6be521090fa444c881e27af026c04e8a /cancellations /6be521090fa444c881e27af026c04e8a /complaints /3a0cc410ab374e2d8a9361dd59436c76",
    " / tenders/ 6be521090fa444c881e27af026c04e8a/ cancellations/ 6be521090fa444c881e27af026c04e8a/ complaints/ 3a0cc410ab374e2d8a9361dd59436c76",
    "Text - / tenders / 6be521090fa444c881e27af026c04e8a / cancellations / 6be521090fa444c881e27af026c04e8a / complaints / 3a0cc410ab374e2d8a9361dd59436c76",
    " / tenders / 6be521090fa444c881e27af026c04e8a / cancellations / 6be521090fa444c881e27af026c04e8a / complaints / 3a0cc410ab374e2d8a9361dd59436c76 - text",
]


class GetComplaintTypeTestCase(unittest.TestCase):
    """
    Test utils.get_complaint_type
    """

    def test_valid_tender_complaint(self):
        for complaint_str in valid_tender_complaint_str:
            self.assertEqual(
                get_complaint_type(complaint_str),
                TENDER_COMPLAINT_TYPE
            )

    def test_valid_qualification_complaint(self):
        for complaint_str in valid_qualification_complaint_str:
            self.assertEqual(
                get_complaint_type(complaint_str),
                QUALIFICATION_COMPLAINT_TYPE
            )

    def test_valid_award_complaint(self):
        for complaint_str in valid_award_complaint_str:
            self.assertEqual(
                get_complaint_type(complaint_str),
                AWARD_COMPLAINT_TYPE
            )

    def test_valid_cancellation_complaint(self):
        for complaint_str in valid_cancellation_complaint_str:
            self.assertEqual(
                get_complaint_type(complaint_str),
                CANCELLATION_COMPLAINT_TYPE
            )


class GetComplaintParamsTestCase(unittest.TestCase):
    """
    Test utils.get_complaint_params
    """

    def test_valid_tender_complaint(self):
        for complaint_str in valid_tender_complaint_str:
            self.assertEqual(
                get_complaint_params(complaint_str, TENDER_COMPLAINT_TYPE),
                {
                    "tender_id": "6be521090fa444c881e27af026c04e8a",
                    "complaint_id": "3a0cc410ab374e2d8a9361dd59436c76",
                }
            )

    def test_valid_qualification_complaint(self):
        for complaint_str in valid_qualification_complaint_str:
            self.assertEqual(
                get_complaint_params(complaint_str, QUALIFICATION_COMPLAINT_TYPE),
                {
                    "tender_id": "6be521090fa444c881e27af026c04e8a",
                    "qualification_id": "6be521090fa444c881e27af026c04e8a",
                    "complaint_id": "3a0cc410ab374e2d8a9361dd59436c76",
                }
            )

    def test_valid_award_complaint(self):
        for complaint_str in valid_award_complaint_str:
            self.assertEqual(
                get_complaint_params(complaint_str, AWARD_COMPLAINT_TYPE),
                {
                    "tender_id": "6be521090fa444c881e27af026c04e8a",
                    "award_id": "6be521090fa444c881e27af026c04e8a",
                    "complaint_id": "3a0cc410ab374e2d8a9361dd59436c76",
                }
            )

    def test_valid_cancellation_complaint(self):
        for complaint_str in valid_cancellation_complaint_str:
            self.assertEqual(
                get_complaint_params(complaint_str, CANCELLATION_COMPLAINT_TYPE),
                {
                    "tender_id": "6be521090fa444c881e27af026c04e8a",
                    "cancellation_id": "6be521090fa444c881e27af026c04e8a",
                    "complaint_id": "3a0cc410ab374e2d8a9361dd59436c76",
                }
            )


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
