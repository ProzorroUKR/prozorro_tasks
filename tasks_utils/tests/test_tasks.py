from environment_settings import (
    API_HOST, API_TOKEN, API_VERSION, DS_HOST, DS_USER, DS_PASSWORD, CONNECT_TIMEOUT,
    READ_TIMEOUT,
)
from tasks_utils.tasks import attach_doc_to_tender, upload_to_doc_service
from celery.exceptions import Retry
from unittest.mock import patch, MagicMock
import requests
import unittest


class AttachToTenderTestCase(unittest.TestCase):

    @patch("tasks_utils.tasks.get_task_result")
    @patch("tasks_utils.tasks.attach_doc_to_tender.retry")
    def test_exception_head(self, retry_mock, get_task_result_mock):
        get_task_result_mock.return_value = None
        retry_mock.side_effect = Retry

        tender_id = "a" * 32
        item_name = "award"
        item_id = "f" * 32
        data = {
            "url": "https://public-docs-sandbox.prozorro.gov.ua/get/3b29ac3b11164f3891e9439cab29053e?KeyID=9d92c6f9&Signature=dbLdN7Jw%252Bj%2F8OYGw57MtydmBpdhsjSMH1KKJwhvg8VWKSRb%252By%2Fmi5mImwBViHcGAwFe5wHu09vbGPIuCQQTIAw%253D%253D",
            "title": "26591010101017J1603101100000000111220172659.KVT",
            "hash": "md5:73ab99ea2d04a128ac0220ac7bb517b7",
            "format": "text/plain"
        }

        with patch("tasks_utils.tasks.requests") as requests_mock:
            requests_mock.head.side_effect = requests.exceptions.ConnectionError

            with self.assertRaises(Retry):
                attach_doc_to_tender(
                    data=data, tender_id=tender_id, item_name=item_name, item_id=item_id
                )

        url = "{host}/api/{version}/tenders/{tender_id}/awards/{award_id}/documents".format(
            host=API_HOST,
            version=API_VERSION,
            award_id=item_id,
            tender_id=tender_id,
        )

        requests_mock.head.assert_called_once_with(
            url,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={
                'Authorization': 'Bearer {}'.format(API_TOKEN),
            }
        )
        requests_mock.post.assert_not_called()

    @patch("tasks_utils.tasks.get_task_result")
    @patch("tasks_utils.tasks.attach_doc_to_tender.retry")
    def test_exception_post(self, retry_mock, get_task_result_mock):
        retry_mock.side_effect = Retry
        get_task_result_mock.return_value = None
        tender_id = "a" * 32
        item_name = "award"
        item_id = "f" * 32
        data = {
            "url": "https://public-docs-sandbox.prozorro.gov.ua/get/3b29ac3b11164f3891e9439cab29053e?KeyID=9d92c6f9&Signature=dbLdN7Jw%252Bj%2F8OYGw57MtydmBpdhsjSMH1KKJwhvg8VWKSRb%252By%2Fmi5mImwBViHcGAwFe5wHu09vbGPIuCQQTIAw%253D%253D",
            "title": "26591010101017J1603101100000000111220172659.KVT",
            "hash": "md5:73ab99ea2d04a128ac0220ac7bb517b7",
            "format": "text/plain"
        }

        with patch("tasks_utils.tasks.requests") as requests_mock:
            requests_mock.head.return_value = MagicMock(
                status_code=200, cookies={"SERVER_ID": "YOUR_MOMS_LAPTOP"}
            )
            requests_mock.post.side_effect = requests.exceptions.ConnectionError

            with self.assertRaises(Retry):
                attach_doc_to_tender(data=data, tender_id=tender_id, item_name=item_name, item_id=item_id)

        url = "{host}/api/{version}/tenders/{tender_id}/awards/{award_id}/documents".format(
            host=API_HOST,
            version=API_VERSION,
            award_id=item_id,
            tender_id=tender_id,
        )

        requests_mock.head.assert_called_once_with(
            url,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={
                'Authorization': 'Bearer {}'.format(API_TOKEN),
            }
        )
        requests_mock.post.assert_called_once_with(
            url,
            json={'data': data},
            cookies={"SERVER_ID": "YOUR_MOMS_LAPTOP"},
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={
                'Authorization': 'Bearer {}'.format(API_TOKEN),
            }
        )

    @patch("tasks_utils.tasks.get_task_result")
    def test_error_post(self, get_task_result_mock):
        get_task_result_mock.return_value = None
        tender_id = "a" * 32
        item_name = "award"
        item_id = "f" * 32
        data = {
            "url": "https://public-docs-sandbox.prozorro.gov.ua/get/3b29ac3b11164f3891e9439cab29053e?KeyID=9d92c6f9&Signature=dbLdN7Jw%252Bj%2F8OYGw57MtydmBpdhsjSMH1KKJwhvg8VWKSRb%252By%2Fmi5mImwBViHcGAwFe5wHu09vbGPIuCQQTIAw%253D%253D",
            "title": "26591010101017J1603101100000000111220172659.KVT",
            "hash": "md5:73ab99ea2d04a128ac0220ac7bb517b7",
            "format": "text/plain"
        }

        with patch("tasks_utils.tasks.requests") as requests_mock:
            requests_mock.head.return_value = MagicMock(
                status_code=200, cookies={"SERVER_ID": "YOUR_MOMS_LAPTOP"}
            )
            requests_mock.post.return_value = MagicMock(status_code=500, text="Unexpected smt")

            with self.assertRaises(Retry):
                attach_doc_to_tender(data=data, tender_id=tender_id, item_name=item_name, item_id=item_id)

        url = "{host}/api/{version}/tenders/{tender_id}/awards/{award_id}/documents".format(
            host=API_HOST,
            version=API_VERSION,
            award_id=item_id,
            tender_id=tender_id,
        )

        requests_mock.head.assert_called_once_with(
            url,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={
                'Authorization': 'Bearer {}'.format(API_TOKEN),
            }
        )
        requests_mock.post.assert_called_once_with(
            url,
            json={'data': data},
            cookies={"SERVER_ID": "YOUR_MOMS_LAPTOP"},
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={
                'Authorization': 'Bearer {}'.format(API_TOKEN),
            }
        )

    @patch("tasks_utils.tasks.save_task_result")
    @patch("tasks_utils.tasks.get_task_result")
    def test_success(self, get_task_result_mock, save_task_result_mock):
        get_task_result_mock.return_value = None
        tender_id = "a" * 32
        item_name = "award"
        item_id = "f" * 32
        data = {
            "url": "https://public-docs-sandbox.prozorro.gov.ua/get/3b29ac3b11164f3891e9439cab29053e?KeyID=9d92c6f9&Signature=dbLdN7Jw%252Bj%2F8OYGw57MtydmBpdhsjSMH1KKJwhvg8VWKSRb%252By%2Fmi5mImwBViHcGAwFe5wHu09vbGPIuCQQTIAw%253D%253D",
            "title": "26591010101017J1603101100000000111220172659.KVT",
            "hash": "md5:73ab99ea2d04a128ac0220ac7bb517b7",
            "format": "text/plain"
        }

        with patch("tasks_utils.tasks.requests") as requests_mock:
            requests_mock.head.return_value = MagicMock(
                status_code=200, cookies={"SERVER_ID": "YOUR_MOMS_LAPTOP"}
            )
            requests_mock.post.return_value = MagicMock(status_code=201)

            attach_doc_to_tender(data=data, tender_id=tender_id, item_name=item_name, item_id=item_id)

        url = "{host}/api/{version}/tenders/{tender_id}/awards/{award_id}/documents".format(
            host=API_HOST,
            version=API_VERSION,
            award_id=item_id,
            tender_id=tender_id,
        )
        requests_mock.head.assert_called_once_with(
            url,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={
                'Authorization': 'Bearer {}'.format(API_TOKEN),
            }
        )
        requests_mock.post.assert_called_once_with(
            url,
            json={'data': data},
            cookies={"SERVER_ID": "YOUR_MOMS_LAPTOP"},
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={
                'Authorization': 'Bearer {}'.format(API_TOKEN),
            }
        )
        get_task_result_mock.assert_called_once_with(
            attach_doc_to_tender,
            (data, tender_id, item_name, item_id)
        )
        save_task_result_mock.assert_called_once_with(
            attach_doc_to_tender,
            True,
            (data, tender_id, item_name, item_id)
        )

    @patch("tasks_utils.tasks.save_task_result")
    @patch("tasks_utils.tasks.requests")
    @patch("tasks_utils.tasks.get_task_result")
    def test_saved_result(self, get_task_result_mock, requests_mock, save_task_result_mock):
        get_task_result_mock.return_value = True
        tender_id = "a" * 32
        item_name = "award"
        item_id = "f" * 32
        data = {
            "url": "https://public-docs-..",
            "title": "26591010101017J1603101100000000111220172659.KVT",
            "hash": "md5:73ab99ea2d04a128ac0220ac7bb517b7",
            "format": "text/plain"
        }

        attach_doc_to_tender(data=data, tender_id=tender_id, item_name=item_name, item_id=item_id)

        requests_mock.head.assert_not_called()
        requests_mock.post.assert_not_called()
        save_task_result_mock.assert_not_called()

    @patch("tasks_utils.tasks.get_task_result")
    def test_exception_post_422(self, get_task_result_mock):
        get_task_result_mock.return_value = None
        tender_id = "a" * 32
        item_name = "award"
        item_id = "f" * 32
        data = {
            "url": "https://public-docs-sandbox.prozorro.gov.ua/get/3b29ac3b11164f3891e9439cab29053e?KeyID=9d92c6f9&Signature=dbLdN7Jw%252Bj%2F8OYGw57MtydmBpdhsjSMH1KKJwhvg8VWKSRb%252By%2Fmi5mImwBViHcGAwFe5wHu09vbGPIuCQQTIAw%253D%253D",
            "title": "26591010101017J1603101100000000111220172659.KVT",
            "hash": "md5:73ab99ea2d04a128ac0220ac7bb517b7",
            "format": "text/plain"
        }

        with patch("tasks_utils.tasks.requests") as requests_mock:
            requests_mock.head.return_value = MagicMock(
                status_code=200, cookies={"SERVER_ID": "YOUR_MOMS_LAPTOP"}
            )
            requests_mock.post.return_value = MagicMock(status_code=422, text="Unexpected smt")

            attach_doc_to_tender(data=data, tender_id=tender_id, item_name=item_name, item_id=item_id)

        url = "{host}/api/{version}/tenders/{tender_id}/awards/{award_id}/documents".format(
            host=API_HOST,
            version=API_VERSION,
            award_id=item_id,
            tender_id=tender_id,
        )

        requests_mock.head.assert_called_once_with(
            url,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={
                'Authorization': 'Bearer {}'.format(API_TOKEN),
            }
        )
        requests_mock.post.assert_called_once_with(
            url,
            json={'data': data},
            cookies={"SERVER_ID": "YOUR_MOMS_LAPTOP"},
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={
                'Authorization': 'Bearer {}'.format(API_TOKEN),
            }
        )

    @patch("tasks_utils.tasks.save_task_result")
    @patch("tasks_utils.tasks.get_task_result")
    def test_exception_post_403(self, get_task_result_mock, save_task_result_mock):
        get_task_result_mock.return_value = None
        tender_id = "a" * 32
        item_name = "award"
        item_id = "f" * 32
        data = {
            "url": "https://public-docs-sandbox.prozorro.gov.ua/get/3b29a",
            "title": "26591010101017J1603101100000000111220172659.KVT",
            "hash": "md5:73ab99ea2d04a128ac0220ac7bb517b7",
            "format": "text/plain"
        }

        with patch("tasks_utils.tasks.requests") as requests_mock:
            requests_mock.head.return_value = MagicMock(
                status_code=200, cookies={"SERVER_ID": "1" * 32}
            )
            requests_mock.post.return_value = MagicMock(
                status_code=403,
                json={"errors": [
                    {
                        "location": "body",
                        "name": "data",
                        "description": "Can't add document in current (complete) tender status"
                    }
                ]}
            )
            attach_doc_to_tender(data=data, tender_id=tender_id, item_name=item_name, item_id=item_id)

        url = "{host}/api/{version}/tenders/{tender_id}/awards/{award_id}/documents".format(
            host=API_HOST,
            version=API_VERSION,
            award_id=item_id,
            tender_id=tender_id,
        )
        requests_mock.head.assert_called_once_with(
            url,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={'Authorization': 'Bearer {}'.format(API_TOKEN)}
        )
        requests_mock.post.assert_called_once_with(
            url,
            json={'data': data},
            cookies={"SERVER_ID": "1" * 32},
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={
                'Authorization': 'Bearer {}'.format(API_TOKEN),
            }
        )
        save_task_result_mock.assert_not_called()


class DSUploadTestCase(unittest.TestCase):

    @patch("tasks_utils.tasks.attach_doc_to_tender")
    @patch("tasks_utils.tasks.get_task_result")
    @patch("tasks_utils.tasks.upload_to_doc_service.retry")
    def test_exception(self, retry_mock, get_task_result_mock, attach_doc_to_tender_mock):
        retry_mock.side_effect = Retry
        get_task_result_mock.return_value = None

        tender_id = "a" * 32
        item_name = "award"
        item_id = "f" * 32
        name = "26591010101017J1603101100000000111220172659.KVT"
        data = "aGVsbG8="

        with patch("tasks_utils.tasks.requests") as requests_mock:
            requests_mock.post.side_effect = requests.exceptions.ConnectionError

            with self.assertRaises(Retry):
                upload_to_doc_service(
                    name=name, content=data, doc_type="",
                    tender_id=tender_id, item_name=item_name, item_id=item_id
                )

        requests_mock.post.assert_called_once_with(
            '{host}/upload'.format(host=DS_HOST),
            auth=(DS_USER, DS_PASSWORD),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            files={'file': (name, b"hello")},
        )
        attach_doc_to_tender_mock.assert_not_called()

    @patch("tasks_utils.tasks.attach_doc_to_tender")
    @patch("tasks_utils.tasks.get_task_result")
    def test_error(self, get_task_result_mock, attach_doc_to_tender_mock):
        get_task_result_mock.return_value = None

        tender_id = "a" * 32
        item_name = "award"
        item_id = "f" * 32
        name = "26591010101017J1603101100000000111220172659.KVT"
        data = "aGVsbG8="

        with patch("tasks_utils.tasks.requests") as requests_mock:
            requests_mock.post.return_value = MagicMock(status_code=500, text="Unexpected smt")

            with self.assertRaises(Retry):
                upload_to_doc_service(
                    name=name, content=data, doc_type="",
                    tender_id=tender_id, item_name=item_name, item_id=item_id
                )

        requests_mock.post.assert_called_once_with(
            '{host}/upload'.format(host=DS_HOST),
            auth=(DS_USER, DS_PASSWORD),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            files={'file': (name, b"hello")},
        )
        attach_doc_to_tender_mock.assert_not_called()

    @patch("tasks_utils.tasks.attach_doc_to_tender")
    @patch("tasks_utils.tasks.save_task_result")
    @patch("tasks_utils.tasks.get_task_result")
    def test_success(self, get_task_result_mock, save_task_result_mock, attach_doc_to_tender_mock):
        get_task_result_mock.return_value = None

        tender_id = "a" * 32
        item_name = "award"
        item_id = "f" * 32
        doc_type = "useless_bytes"
        data = "aGk="
        name = "26591010101017J1603101100000000111220172659.KVT"

        with patch("tasks_utils.tasks.requests") as requests_mock:
            file_data = {
                "url": "https://localhost/get/123?KeyID=123&Signature=QQQ",
                "title": name,
                "hash": "md5:9af9e74cfa0e6f4438008ef7268a3716",
                "format": "application/octet-stream"
            }
            requests_mock.post.return_value = MagicMock(
                status_code=200,
                json=lambda: {
                    "get_url": "https://localhost/get/123?KeyID=123&Expires=1552926631&Signature=QQQ",
                    "data": file_data
                }
            )

            upload_to_doc_service(
                name=name, content=data, doc_type=doc_type,
                tender_id=tender_id, item_name=item_name, item_id=item_id
            )

        requests_mock.post.assert_called_once_with(
            '{host}/upload'.format(host=DS_HOST),
            auth=(DS_USER, DS_PASSWORD),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            files={'file': (name, b"hi")},
        )
        attach_doc_to_tender_mock.delay.assert_called_once_with(
            item_name="award",
            item_id='f' * 32,
            data=file_data,
            tender_id='a' * 32
        )
        get_task_result_mock.assert_called_once_with(
            upload_to_doc_service,
            (name, data, doc_type, tender_id, item_name, item_id)
        )
        save_task_result_mock.assert_called_once_with(
            upload_to_doc_service,
            file_data,
            (name, data, doc_type, tender_id, item_name, item_id)
        )
