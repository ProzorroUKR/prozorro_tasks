from edr_bot.settings import VERSION, DOC_AUTHOR
from edr_bot.tasks import get_edr_data
from uuid import uuid4
from unittest.mock import patch, Mock, call
from celery.exceptions import Retry
import unittest
import requests


@patch('celery_worker.locks.get_mongodb_collection',
       Mock(return_value=Mock(find_one=Mock(return_value=None))))
class TestHandlerCase(unittest.TestCase):

    def test_handle_connection_error(self):
        code = "1234"
        tender_id, item_name, item_id = "f" * 32, "award", "a" * 32

        with patch("edr_bot.tasks.requests") as requests_mock:
            requests_mock.get.side_effect = requests.exceptions.ConnectionError()

            get_edr_data.retry = Mock(side_effect=Retry)
            with self.assertRaises(Retry):
                get_edr_data(code, tender_id, item_name, item_id)

            get_edr_data.retry.assert_called_once_with(exc=requests_mock.get.side_effect)

    def test_handle_429_response(self):
        code = "1234"
        tender_id, item_name, item_id = "f" * 32, "award", "a" * 32

        with patch("edr_bot.tasks.requests") as requests:
            requests.get.return_value = Mock(
                status_code=429,
                headers={'Retry-After': "13"}
            )

            get_edr_data.retry = Mock(side_effect=get_edr_data.retry)
            with self.assertRaises(Retry):
                get_edr_data(code, tender_id, item_name, item_id)

            get_edr_data.retry.assert_called_once_with(countdown=13)

    @patch("edr_bot.tasks.upload_to_doc_service")
    def test_handle_404_response(self, upload_to_doc_service):
        code = "1234"
        tender_id, item_name, item_id = "f" * 32, "award", "a" * 32

        ret_aft, resp_id = 13, uuid4().hex
        source_date = ["2018-12-25T19:00:00+02:00"]
        with patch("edr_bot.tasks.requests") as requests:
            requests.get.return_value = Mock(
                status_code=404,
                json=Mock(return_value={
                    'errors': [
                        {
                            'description': [
                                {
                                    "error": {
                                        "errorDetails": "Couldn't find this code in EDR.",
                                        "code": "notFound"
                                    },
                                    "meta": {"detailsSourceDate": source_date}
                                }
                            ]
                        }
                    ]
                }),
                headers={
                    'X-Request-ID': resp_id,
                    'content-type': 'application/json',
                    'User-agent': 'prozorro_tasks',
                }
            )

            with patch("edr_bot.tasks.uuid4") as uuid4_mock:
                uuid4_mock.return_value = Mock(hex="b" * 32)
                get_edr_data(code, tender_id, item_name, item_id)

        upload_to_doc_service.delay.assert_called_once_with(
            data={
                'error': {
                    'errorDetails': "Couldn't find this code in EDR.",
                    'code': 'notFound'
                },
                'meta': {
                    'detailsSourceDate': source_date,
                    'id': "b" * 32,
                    'author': 'IdentificationBot',
                    'sourceRequests': [resp_id],
                    'version': '2.0.0'
                 }
            },
            tender_id=tender_id,
            item_name=item_name,
            item_id=item_id
        )

    @patch("edr_bot.tasks.upload_to_doc_service")
    def test_handle_200_response(self, upload_to_doc_service):
        code = "1234"
        response_id = uuid4().hex
        tender_id, item_name, item_id = "f" * 32, "award", "a" * 32
        source_date = ["2018-12-25T19:00:00+02:00"]

        with patch("edr_bot.tasks.requests") as requests_mock:
            requests_mock.get.return_value = Mock(
                status_code=200,
                json=Mock(return_value={
                    'data': [{"test": 1}],
                    "meta": {"detailsSourceDate": source_date}
                }),
                headers={
                    'X-Request-ID': response_id,
                    'User-agent': 'prozorro_tasks',
                }
            )
            with patch("edr_bot.tasks.uuid4") as uuid4_mock:
                uuid4_mock.return_value = Mock(hex="b" * 32)
                get_edr_data(code, tender_id, item_name, item_id)

        self.assertEqual(
            upload_to_doc_service.delay.call_args_list,
            [
                call(
                    data={
                        'meta': {
                            'sourceDate': source_date[0],
                            'id': "b" * 32,
                            'author': DOC_AUTHOR,
                            'sourceRequests': [response_id],
                            'version': VERSION
                        },
                        'data': {'test': 1}
                    },
                    item_id=item_id,
                    item_name=item_name,
                    tender_id=tender_id
                )
            ]
        )

    @patch("edr_bot.tasks.upload_to_doc_service")
    def test_handle_200_two_response(self, upload_to_doc_service):
        code = "1234"
        response_id = uuid4().hex
        tender_id, item_name, item_id = "f" * 32, "award", "a" * 32
        source_date = ["2018-12-25T19:00:00+02:00"]

        with patch("edr_bot.tasks.requests") as requests_mock:
            requests_mock.get.return_value = Mock(
                status_code=200,
                json=Mock(return_value={
                    'data': [{"test": 1}, {"test": 2}],
                    "meta": {"detailsSourceDate": source_date}
                }),
                headers={
                    'X-Request-ID': response_id,
                    'User-agent': 'prozorro_tasks',
                }
            )
            with patch("edr_bot.tasks.uuid4") as uuid4_mock:
                uuid4_mock.return_value = Mock(hex="b" * 32)
                get_edr_data(code, tender_id, item_name, item_id)

        self.assertEqual(
            upload_to_doc_service.delay.call_args_list,
            [
                call(
                    data={
                        'meta': {
                            'sourceDate': source_date[0],
                            'id': '{}.2.1'.format("b" * 32),
                            'author': DOC_AUTHOR,
                            'sourceRequests': [response_id],
                            'version': VERSION
                        },
                        'data': {'test': 1}
                    },
                    item_id=item_id,
                    item_name=item_name,
                    tender_id=tender_id
                ),
                call(
                    data={
                        'meta': {
                            'sourceDate': None,
                            'id': '{}.2.2'.format("b" * 32),
                            'author': DOC_AUTHOR,
                            'sourceRequests': [response_id],
                            'version': VERSION
                        },
                        'data': {'test': 2}
                    },
                    item_id=item_id,
                    item_name=item_name,
                    tender_id=tender_id
                )
            ]
        )
