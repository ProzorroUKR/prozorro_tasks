from edr_bot.settings import DEFAULT_RETRY_AFTER
from edr_bot.tasks import process_tender
from uuid import uuid4
from unittest.mock import patch, Mock, call
from celery.exceptions import Retry
import unittest
import requests


class TestHandlerCase(unittest.TestCase):

    def test_handle_connection_error(self):
        tender_id = "f" * 32

        with patch("edr_bot.tasks.requests") as requests_mock:
            requests_mock.get.side_effect = requests.exceptions.ConnectionError()

            process_tender.retry = Mock(side_effect=Retry)
            with self.assertRaises(Retry):
                process_tender(tender_id)

            process_tender.retry.assert_called_once_with(exc=requests_mock.get.side_effect)

    def test_handle_429_response(self):
        tender_id = "f" * 32

        ret_aft = 13
        with patch("edr_bot.tasks.requests") as requests_mock:
            requests_mock.get.return_value = Mock(
                status_code=429,
                headers={'Retry-After': ret_aft}
            )

            process_tender.retry = Mock(side_effect=Retry)
            with self.assertRaises(Retry):
                process_tender(tender_id)

                process_tender.retry.assert_called_once_with(countdown=ret_aft)

    def test_handle_500_response(self):
        tender_id = "f" * 32

        with patch("edr_bot.tasks.requests") as requests_mock:
            requests_mock.get.return_value = Mock(
                status_code=500,
                headers={}
            )

            process_tender.retry = Mock(side_effect=Retry)
            with self.assertRaises(Retry):
                process_tender(tender_id)

            process_tender.retry.assert_called_once_with(countdown=DEFAULT_RETRY_AFTER)

    def test_handle_404_response(self):
        """
        This is an unexpected case, so it's handled the same way with retry()
        Can be caused by sync problems between database hosts, so retry() might help
        """
        tender_id = "f" * 32

        with patch("edr_bot.tasks.requests") as requests_mock:
            requests_mock.get.return_value = Mock(
                status_code=404,
                headers={}
            )

            process_tender.retry = Mock(side_effect=Retry)
            with self.assertRaises(Retry):
                process_tender(tender_id)

            process_tender.retry.assert_called_once_with(countdown=DEFAULT_RETRY_AFTER)

    @patch("edr_bot.tasks.get_edr_data")
    def test_handle_200_response_award(self, get_edr_data):
        code_1 = "758234578270346"
        code_2 = "758234578270347"
        response_id = uuid4().hex
        tender_id, item_name, item_id = "f" * 32, "award", "a" * 32

        with patch("edr_bot.tasks.requests") as requests_mock:
            requests_mock.get.return_value = Mock(
                status_code=200,
                json=Mock(return_value={
                    'data': {
                        'id': tender_id,
                        'awards': [
                            {
                                'status': 'cancelled',
                            },
                            {
                                'status': 'pending',
                                'documents': [
                                    {
                                        "documentType": "registerExtract",
                                    }
                                ]
                            },
                            {
                                "id": item_id,
                                "status": "pending",  # it's not a real case (two pending awards);for test purpose only
                                "suppliers": [
                                    {
                                        "identifier": {
                                            "scheme": "UA-EDR",
                                            "id": code_1,
                                        },
                                    },
                                    {
                                        "identifier": {
                                            "scheme": "UA-EDR",
                                            "id": code_2,
                                        },
                                    }
                                ],
                            },
                        ]
                    },
                }),
                headers={'X-Request-ID': response_id}
            )

            process_tender(tender_id)

        self.assertEqual(
            get_edr_data.delay.call_args_list,
            [
                call(
                    code=code_1,
                    request_id=response_id,
                    item_id=item_id,
                    item_name=item_name,
                    tender_id=tender_id
                ),
                call(
                    code=code_2,
                    request_id=response_id,
                    item_id=item_id,
                    item_name=item_name,
                    tender_id=tender_id
                )
            ]
        )

    @patch("edr_bot.tasks.get_edr_data")
    def test_handle_200_response_award_lot_is_missed(self, get_edr_data):
        code = "758234578270346"
        response_id = uuid4().hex
        tender_id, item_name, item_id = "f" * 32, "award", "a" * 32

        with patch("edr_bot.tasks.requests") as requests_mock:
            requests_mock.get.return_value = Mock(
                status_code=200,
                json=Mock(return_value={
                    'data': {
                        'id': tender_id,
                        'lots': [
                            {
                                'id': "test321",
                                'status': "cancelled",
                            },
                            {
                                'id': "test123",
                                'status': "active",
                            },
                        ],
                        'awards': [
                            {
                                "id": item_id,
                                "bid_id": "a" * 32,
                                "lotID": "qwerty",
                                "status": "pending",
                                "suppliers": [
                                    {
                                        "identifier": {
                                            "scheme": "UA-EDR",
                                            "id": code,
                                        },
                                    },
                                ],
                            },
                        ]
                    },
                }),
                headers={'X-Request-ID': response_id}
            )

            process_tender(tender_id)

        get_edr_data.delay.assert_not_called()

    @patch("edr_bot.tasks.get_edr_data")
    def test_handle_200_response_qualification(self, get_edr_data):
        code_1 = "758234578270346"
        code_2 = "758234578270347"
        response_id = uuid4().hex
        tender_id, item_name, item_id = "f" * 32, "qualification", "a" * 32

        with patch("edr_bot.tasks.requests") as requests_mock:
            requests_mock.get.return_value = Mock(
                status_code=200,
                json=Mock(return_value={
                    'data': {
                        'id': tender_id,
                        'bids': [
                            {
                                'id': 'qwerty',
                                'tenderers': [
                                    {
                                        "identifier": {
                                            "scheme": "UA-EDR",
                                            "id": code_1,
                                        },
                                    },
                                    {
                                        "identifier": {
                                            "scheme": "UA-EDR",
                                            "id": code_2,
                                        },
                                    }
                                ]
                            }
                        ],
                        'qualifications': [
                            {
                                'status': 'cancelled',
                            },
                            {
                                'status': 'pending',
                                'documents': [
                                    {
                                        "documentType": "registerExtract",
                                    }
                                ]
                            },
                            {
                                "id": item_id,
                                "bidID": "qwerty",
                                "status": "pending",  # it's not a real case (two pending awards);for test purpose only
                            },
                        ]
                    },
                }),
                headers={'X-Request-ID': response_id}
            )

            process_tender(tender_id)

        self.assertEqual(
            get_edr_data.delay.call_args_list,
            [
                call(
                    code=code_1,
                    request_id=response_id,
                    item_id=item_id,
                    item_name=item_name,
                    tender_id=tender_id
                )
            ]
        )

    @patch("edr_bot.tasks.get_edr_data")
    def test_handle_200_response_qualification_tenderers_are_missed(self, get_edr_data):
        response_id = uuid4().hex
        tender_id, item_name, item_id = "f" * 32, "qualification", "a" * 32
        bid_id = 'qwerty'

        with patch("edr_bot.tasks.requests") as requests_mock:
            requests_mock.get.return_value = Mock(
                status_code=200,
                json=Mock(return_value={
                    'data': {
                        'id': tender_id,
                        'bids': [
                            {
                                'id': bid_id,
                            }
                        ],
                        'qualifications': [
                            {
                                "id": item_id,
                                "bidID": bid_id,
                                "status": "pending",
                            },
                        ]
                    },
                }),
                headers={'X-Request-ID': response_id}
            )

            process_tender(tender_id)

        get_edr_data.delay.assert_not_called()

    @patch("edr_bot.tasks.get_edr_data")
    def test_handle_200_response_qualification_bid_is_missed(self, get_edr_data):
        response_id = uuid4().hex
        tender_id, item_name, item_id = "f" * 32, "qualification", "a" * 32
        bid_id = 'qwerty'

        with patch("edr_bot.tasks.requests") as requests_mock:
            requests_mock.get.return_value = Mock(
                status_code=200,
                json=Mock(return_value={
                    'data': {
                        'id': tender_id,
                        'qualifications': [
                            {
                                "id": item_id,
                                "bidID": bid_id,
                                "status": "pending",
                            },
                        ]
                    },
                }),
                headers={'X-Request-ID': response_id}
            )

            process_tender(tender_id)

        get_edr_data.delay.assert_not_called()
