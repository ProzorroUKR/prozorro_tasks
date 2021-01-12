from unittest.mock import patch, Mock, call
from environment_settings import PUBLIC_API_HOST, API_VERSION, CONNECT_TIMEOUT, READ_TIMEOUT
from celery.exceptions import Retry
from fiscal_bot.tasks import process_tender
import requests
import unittest


class TenderTestCase(unittest.TestCase):

    @patch("fiscal_bot.tasks.process_tender.retry")
    @patch("fiscal_bot.tasks.prepare_receipt_request")
    @patch("fiscal_bot.tasks.requests")
    def test_handle_exception(self, requests_mock, prepare_receipt_request, retry_mock):
        retry_mock.side_effect = Retry
        tender_id = "f" * 32
        requests_mock.get.side_effect = requests.exceptions.ConnectionError()

        with self.assertRaises(Retry):
            process_tender(tender_id)

        requests_mock.get.assert_called_once_with(
            "{host}/api/{version}/tenders/{tender_id}".format(
                host=PUBLIC_API_HOST,
                version=API_VERSION,
                tender_id=tender_id,
            ),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )
        prepare_receipt_request.assert_not_called()
        retry_mock.assert_called_once_with(exc=requests_mock.get.side_effect)

    @patch("fiscal_bot.tasks.process_tender.retry")
    @patch("fiscal_bot.tasks.prepare_receipt_request")
    @patch("fiscal_bot.tasks.requests")
    def test_handle_error(self, requests_mock, prepare_receipt_request, retry_mock):
        retry_mock.side_effect = Retry
        tender_id = "f" * 32
        requests_mock.get.return_value = Mock(
            status_code=502,
            text="Bad Gateway",
            headers={"Retry-After": 10}
        )

        with self.assertRaises(Retry):
            process_tender(tender_id)

        requests_mock.get.assert_called_once_with(
            "{host}/api/{version}/tenders/{tender_id}".format(
                host=PUBLIC_API_HOST,
                version=API_VERSION,
                tender_id=tender_id,
            ),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )
        prepare_receipt_request.assert_not_called()
        retry_mock.assert_called_once_with(countdown=10)

    @patch("fiscal_bot.tasks.prepare_receipt_request")
    def test_handle_200_response(self, prepare_receipt_request):
        code_1 = "1" * 8
        code_2 = "2" * 10
        tender_id, item_id = "f" * 32, "a" * 32
        tenderID = "UA-0000"

        with patch("fiscal_bot.tasks.requests") as requests_mock:
            requests_mock.get.return_value = Mock(
                status_code=200,
                json=Mock(return_value={
                    'data': {
                        'id': tender_id,
                        'tenderID': tenderID,
                        'awards': [
                            {
                                'status': 'cancelled',
                            },
                            {
                                'status': 'pending',
                            },
                            {
                                "id": item_id,
                                "status": "active",
                                "date": "2019-06-07T14:27:03.148663+03:00",
                                "suppliers": [
                                    {
                                        "identifier": {
                                            "scheme": "UA-EDR",
                                            "legalName": 'Wow',
                                            "id": code_1,
                                        },
                                    }
                                ],
                            },
                            {
                                "id": item_id,
                                "status": "active",
                                "date": "2019-07-01T14:27:03.148663+03:00",
                                "suppliers": [
                                    {
                                        "identifier": {
                                            "scheme": "UA-EDR",
                                            "legalName": 'OOO "Моя оборона"',
                                            "id": code_1,
                                        },
                                    },
                                    {
                                        "identifier": {
                                            "scheme": "UA-EDR",
                                            "id": code_2,
                                        },
                                        "name": "Monty",
                                    },
                                    {
                                        "identifier": {
                                            "scheme": "UA-WTF",
                                            "id": code_1,
                                        },
                                    }
                                ],
                            },
                        ]
                    },
                })
            )

            process_tender(tender_id)

            self.assertEqual(
                prepare_receipt_request.delay.call_args_list,
                [
                    call(
                        supplier=dict(
                            identifier=code_1,
                            name='OOO "Моя оборона"',
                            award_id=item_id,
                            tender_id=tender_id,
                            tenderID=tenderID,
                            lot_index=None,
                        )
                    ),
                    call(
                        supplier=dict(
                            identifier=code_2,
                            name="Monty",
                            award_id=item_id,
                            tender_id=tender_id,
                            tenderID=tenderID,
                            lot_index=None,
                        )
                    )
                ]
            )

    @patch("fiscal_bot.tasks.prepare_receipt_request")
    def test_handle_200_with_lots_response(self, prepare_receipt_request):
        code_1 = "1" * 8
        code_2 = "2" * 10
        tender_id, item_id = "f" * 32, "a" * 32
        tenderID = "UA-0000"

        with patch("fiscal_bot.tasks.requests") as requests_mock:
            requests_mock.get.return_value = Mock(
                status_code=200,
                json=Mock(return_value={
                    'data': {
                        'id': tender_id,
                        'tenderID': tenderID,
                        'awards': [
                            {
                                "id": item_id,
                                "status": "active",
                                "lotID": "1234",
                                "date": "2019-07-01T14:27:03.148663+03:00",
                                "suppliers": [
                                    {
                                        "identifier": {
                                            "scheme": "UA-EDR",
                                            "legalName": 'OOO "Моя оборона"',
                                            "id": code_1,
                                        },
                                    },
                                ],
                            },
                            {
                                "id": item_id,
                                "status": "active",
                                "lotID": "1",
                                "date": "2019-07-01T14:27:03.148663+03:00",
                                "suppliers": [
                                    {
                                        "identifier": {
                                            "scheme": "UA-EDR",
                                            "id": code_2,
                                        },
                                        "name": "Monty",
                                    },
                                ],
                            },
                        ],
                        "lots": [
                            {"id": "1"},
                            {"id": "12"},
                            {"id": "123"},
                            {"id": "1234"},
                            {"id": "12345"},
                        ],
                    },
                })
            )

            process_tender(tender_id)

            self.assertEqual(
                prepare_receipt_request.delay.call_args_list,
                [
                    call(
                        supplier=dict(
                            identifier=code_1,
                            name='OOO "Моя оборона"',
                            award_id=item_id,
                            tender_id=tender_id,
                            tenderID=tenderID,
                            lot_index=3,
                        )
                    ),
                    call(
                        supplier=dict(
                            identifier=code_2,
                            name="Monty",
                            award_id=item_id,
                            tender_id=tender_id,
                            tenderID=tenderID,
                            lot_index=0,
                        )
                    )
                ]
            )
