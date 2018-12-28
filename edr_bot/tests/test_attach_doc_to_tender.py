from edr_bot.settings import CONNECT_TIMEOUT, READ_TIMEOUT
from environment_settings import API_TOKEN, API_VERSION, API_HOST
from edr_bot.tasks import attach_doc_to_tender
from unittest.mock import patch, Mock
from celery.exceptions import Retry
import unittest
import requests


class AttachDocTestCase(unittest.TestCase):

    def test_handle_head_connection_error(self):
        data, tender_id, item_name, item_id = {"meta": {"id": 1}, "data": {}}, "f" * 32, "award", "a" * 32

        with patch("edr_bot.tasks.requests") as requests_mock:
            requests_mock.head.side_effect = requests.exceptions.ConnectionError()

            attach_doc_to_tender.retry = Mock(side_effect=Retry)
            with self.assertRaises(Retry):
                attach_doc_to_tender(data=data, tender_id=tender_id, item_name=item_name, item_id=item_id)

            attach_doc_to_tender.retry.assert_called_once_with(exc=requests_mock.head.side_effect)

    def test_handle_post_connection_error(self):
        data, tender_id, item_name, item_id = {"meta": {"id": 1}, "data": {}}, "f" * 32, "award", "a" * 32

        with patch("edr_bot.tasks.requests") as requests_mock:
            requests_mock.post.side_effect = requests.exceptions.ConnectionError()

            attach_doc_to_tender.retry = Mock(side_effect=Retry)
            with self.assertRaises(Retry):
                attach_doc_to_tender(data=data, tender_id=tender_id, item_name=item_name, item_id=item_id)

            attach_doc_to_tender.retry.assert_called_once_with(exc=requests_mock.post.side_effect)

    def test_handle_head_429_response(self):
        data, tender_id, item_name, item_id = {"meta": {"id": 1}, "data": {'test': 3}}, "f" * 32, "award", "a" * 32

        ret_aft, server_id = 13, "e" * 32
        with patch("edr_bot.tasks.requests") as requests_mock:
            requests_mock.head.return_value = Mock(
                status_code=429,
                headers={'Retry-After': ret_aft},
                cookies={'SERVER_ID': server_id}
            )
            requests_mock.post.return_value = Mock(status_code=201)
            attach_doc_to_tender.retry = Mock(side_effect=Retry)

            attach_doc_to_tender(data=data, tender_id=tender_id, item_name=item_name, item_id=item_id)

            requests_mock.post.assert_called_once_with(
                "{host}/api/{version}/tenders/{tender_id}/{item_name}s/{item_id}/documents".format(
                    host=API_HOST,
                    version=API_VERSION,
                    item_name=item_name,
                    item_id=item_id,
                    tender_id=tender_id,
                ),
                json={'data': data['data']},
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                headers={
                    'Authorization': 'Bearer {}'.format(API_TOKEN),
                    'X-Client-Request-ID': data['meta']['id'],
                },
                cookies={'SERVER_ID': server_id},
            )
            attach_doc_to_tender.retry.assert_not_called()

    def test_handle_post_429_response(self):
        data, tender_id, item_name, item_id = {"meta": {"id": 1}, "data": {'test': 3}}, "f" * 32, "award", "a" * 32

        ret_aft, server_id = 13, "e" * 32
        with patch("edr_bot.tasks.requests") as requests_mock:
            requests_mock.post.return_value = Mock(
                status_code=429,
                headers={'Retry-After': ret_aft},
            )
            requests_mock.head.return_value = Mock(cookies={'SERVER_ID': server_id})

            attach_doc_to_tender.retry = Mock(side_effect=Retry)
            with self.assertRaises(Retry):
                attach_doc_to_tender(data=data, tender_id=tender_id, item_name=item_name, item_id=item_id)

            requests_mock.post.assert_called_once_with(
                "{host}/api/{version}/tenders/{tender_id}/{item_name}s/{item_id}/documents".format(
                    host=API_HOST,
                    version=API_VERSION,
                    item_name=item_name,
                    item_id=item_id,
                    tender_id=tender_id,
                ),
                json={'data': data['data']},
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                headers={
                    'Authorization': 'Bearer {}'.format(API_TOKEN),
                    'X-Client-Request-ID': data['meta']['id'],
                },
                cookies={'SERVER_ID': server_id},
            )

    def test_handle_post_422_response(self):
        data, tender_id, item_name, item_id = {"meta": {"id": 1}, "data": {'test': 3}}, "f" * 32, "award", "a" * 32

        ret_aft, server_id = 13, "e" * 32
        with patch("edr_bot.tasks.requests") as requests_mock:
            requests_mock.post.return_value = Mock(
                status_code=422,
                headers={'Retry-After': ret_aft},
            )
            requests_mock.head.return_value = Mock(cookies={'SERVER_ID': server_id})
            attach_doc_to_tender.retry = Mock(side_effect=Retry)

            attach_doc_to_tender(data=data, tender_id=tender_id, item_name=item_name, item_id=item_id)

            requests_mock.post.assert_called_once_with(
                "{host}/api/{version}/tenders/{tender_id}/{item_name}s/{item_id}/documents".format(
                    host=API_HOST,
                    version=API_VERSION,
                    item_name=item_name,
                    item_id=item_id,
                    tender_id=tender_id,
                ),
                json={'data': data['data']},
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                headers={
                    'Authorization': 'Bearer {}'.format(API_TOKEN),
                    'X-Client-Request-ID': data['meta']['id'],
                },
                cookies={'SERVER_ID': server_id},
            )
            attach_doc_to_tender.retry.assert_not_called()

