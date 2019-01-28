from environment_settings import PUBLIC_API_HOST, API_VERSION
from crawler.settings import (
    API_LIMIT, API_OPT_FIELDS, CONNECT_TIMEOUT, READ_TIMEOUT,
    FEED_URL_TEMPLATE, WAIT_MORE_RESULTS_COUNTDOWN
)
from unittest.mock import patch, Mock, call
from celery.exceptions import Retry
import unittest
import requests
with patch('celery_worker.locks.unique_task_decorator', lambda x: x):
    from crawler.tasks import process_feed


class ProcessTestCase(unittest.TestCase):

    def test_handle_connection_error(self):

        with patch("crawler.tasks.requests") as requests_mock:
            requests_mock.get.side_effect = requests.exceptions.ConnectionError()

            process_feed.retry = Mock(side_effect=Retry)
            with self.assertRaises(Retry):
                process_feed()

            process_feed.retry.assert_called_once_with(exc=requests_mock.get.side_effect)

    def test_handle_429_response(self):

        ret_aft = 13
        with patch("crawler.tasks.requests") as requests_mock:
            requests_mock.get.return_value = Mock(
                status_code=429,
                headers={'Retry-After': ret_aft}
            )

            process_feed.retry = Mock(side_effect=Retry)
            with self.assertRaises(Retry):
                process_feed()

            process_feed.retry.assert_called_once_with(countdown=ret_aft)

    def test_start_crawler_few_results(self):
        server_id = "a" * 32
        with patch("crawler.tasks.requests") as requests_mock:
            requests_mock.utils.dict_from_cookiejar = requests_mock.utils.cookiejar_from_dict = lambda d: d
            requests_mock.get.return_value = Mock(
                status_code=200,
                cookies={'SERVER_ID': server_id},
                json=Mock(return_value={
                    'data': [
                        {
                            "id": uid
                        }
                        for uid in range(API_LIMIT - 1)
                    ],
                    'next_page': {
                        'offset': -1
                    },
                    'prev_page': {
                        'offset': 1
                    },
                }),
            )
            process_feed.apply_async = Mock()
            process_feed()

            requests_mock.get.assert_called_once_with(
                FEED_URL_TEMPLATE.format(
                    host=PUBLIC_API_HOST,
                    version=API_VERSION,
                    limit=API_LIMIT,
                    opt_fields="%2C".join(API_OPT_FIELDS),
                    resource="tenders",
                    descending="1",
                    offset=""
                ),
                cookies={},
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )

        self.assertEqual(
            process_feed.apply_async.call_args_list,
            [
                call(
                    countdown=60,
                    kwargs={
                        'offset': 1,
                        'cookies': {'SERVER_ID': server_id}
                    }
                ),
            ],
            msg="Only forward crawling since len(data) < API_LIMIT"
        )

    def test_start_crawler(self):
        server_id = "a" * 32
        with patch("crawler.tasks.requests") as requests_mock:
            requests_mock.utils.dict_from_cookiejar = requests_mock.utils.cookiejar_from_dict = lambda d: d
            requests_mock.get.return_value = Mock(
                status_code=200,
                cookies={'SERVER_ID': server_id},
                json=Mock(return_value={
                    'data': [
                        {
                            "id": uid
                        }
                        for uid in range(API_LIMIT)
                    ],
                    'next_page': {
                        'offset': -1
                    },
                    'prev_page': {
                        'offset': 1
                    },
                }),
            )
            process_feed.apply_async = Mock()
            process_feed()

            requests_mock.get.assert_called_once_with(
                FEED_URL_TEMPLATE.format(
                    host=PUBLIC_API_HOST,
                    version=API_VERSION,
                    limit=API_LIMIT,
                    opt_fields="%2C".join(API_OPT_FIELDS),
                    resource="tenders",
                    descending="1",
                    offset=""
                ),
                cookies={},
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )

        self.assertEqual(
            process_feed.apply_async.call_args_list,
            [
                call(
                    kwargs={
                        'offset': -1,
                        'descending': '1',
                        'cookies': {'SERVER_ID': server_id}
                    }
                ),
                call(
                    countdown=60,
                    kwargs={
                        'offset': 1,
                        'cookies': {'SERVER_ID': server_id}
                    }
                ),
            ],
            msg="Only forward crawling since len(data) < API_LIMIT"
        )

    def test_proceed_forward_crawler(self):
        server_id = "a" * 32
        with patch("crawler.tasks.requests") as requests_mock:
            requests_mock.utils.cookiejar_from_dict = lambda d: d
            requests_mock.get.return_value = Mock(
                status_code=200,
                json=Mock(return_value={
                    'data': [
                        {
                            "id": uid
                        }
                        for uid in range(API_LIMIT)
                    ],
                    'next_page': {
                        'offset': 2
                    },
                    'prev_page': {
                        'offset': 0
                    },
                }),
                cookies={}
            )
            process_feed.apply_async = Mock()
            process_feed(offset=1, cookies={'SERVER_ID': server_id})

            requests_mock.get.assert_called_once_with(
                FEED_URL_TEMPLATE.format(
                    host=PUBLIC_API_HOST,
                    version=API_VERSION,
                    resource="tenders",
                    descending="",
                    offset=1,
                    limit=API_LIMIT,
                    opt_fields="%2C".join(API_OPT_FIELDS)
                ),
                cookies={'SERVER_ID': server_id},
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )

        process_feed.apply_async.assert_called_once_with(
            kwargs={
                'offset': 2,
                'descending': '',
                'cookies': {'SERVER_ID': server_id}
            }
        )

    @patch("crawler.tasks.datetime")
    def test_proceed_forward_crawler_few_results(self, datetime_mock):
        now = '2019-01-28T09:15:04.476981+02:00'
        datetime_mock.now.return_value.isoformat.return_value = now
        server_id = "a" * 32
        with patch("crawler.tasks.requests") as requests_mock:
            requests_mock.utils.cookiejar_from_dict = lambda d: d
            requests_mock.get.return_value = Mock(
                status_code=200,
                json=Mock(return_value={
                    'data': [
                        {
                            "id": uid
                        }
                        for uid in range(API_LIMIT - 1)
                    ],
                    'next_page': {
                        'offset': 2
                    },
                    'prev_page': {
                        'offset': 0
                    },
                }),
                cookies={}
            )
            process_feed.apply_async = Mock()
            process_feed(offset=1, cookies={'SERVER_ID': server_id})

            requests_mock.get.assert_called_once_with(
                FEED_URL_TEMPLATE.format(
                    host=PUBLIC_API_HOST,
                    version=API_VERSION,
                    resource="tenders",
                    descending="",
                    offset=1,
                    limit=API_LIMIT,
                    opt_fields="%2C".join(API_OPT_FIELDS)
                ),
                cookies={'SERVER_ID': server_id},
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )

        process_feed.apply_async.assert_called_once_with(
            kwargs={
                'offset': 2,
                'descending': '',
                'cookies': {'SERVER_ID': server_id},
                'timestamp': now
            },
            countdown=WAIT_MORE_RESULTS_COUNTDOWN
        )

    def test_proceed_backward_crawler(self):
        server_id = "a" * 32
        with patch("crawler.tasks.requests") as requests_mock:
            requests_mock.utils.cookiejar_from_dict = lambda d: d
            requests_mock.get.return_value = Mock(
                status_code=200,
                json=Mock(return_value={
                    'data': [
                        {
                            "id": uid
                        }
                        for uid in range(API_LIMIT)
                    ],
                    'next_page': {
                        'offset': -2
                    },
                    'prev_page': {
                        'offset': 0
                    },
                }),
                cookies={}
            )
            process_feed.apply_async = Mock()
            process_feed(offset=-1, descending=1, cookies={'SERVER_ID': server_id})

            requests_mock.get.assert_called_once_with(
                FEED_URL_TEMPLATE.format(
                    host=PUBLIC_API_HOST,
                    version=API_VERSION,
                    resource="tenders",
                    descending=1,
                    offset=-1,
                    limit=API_LIMIT,
                    opt_fields="%2C".join(API_OPT_FIELDS)
                ),
                cookies={'SERVER_ID': server_id},
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )

        process_feed.apply_async.assert_called_once_with(
            kwargs={
                'offset': -2,
                'descending': 1,
                'cookies': {'SERVER_ID': server_id}
            }
        )

    def test_proceed_backward_crawler_few_results(self):
        server_id = "a" * 32
        with patch("crawler.tasks.requests") as requests_mock:
            requests_mock.utils.cookiejar_from_dict = lambda d: d
            requests_mock.get.return_value = Mock(
                status_code=200,
                json=Mock(return_value={
                    'data': [
                        {
                            "id": uid
                        }
                        for uid in range(API_LIMIT - 1)
                    ],
                    'next_page': {
                        'offset': -2
                    },
                    'prev_page': {
                        'offset': 0
                    },
                }),
                cookies={}
            )
            process_feed.apply_async = Mock()
            process_feed(offset=-1, descending=1, cookies={'SERVER_ID': server_id})

            requests_mock.get.assert_called_once_with(
                FEED_URL_TEMPLATE.format(
                    host=PUBLIC_API_HOST,
                    version=API_VERSION,
                    resource="tenders",
                    descending=1,
                    offset=-1,
                    limit=API_LIMIT,
                    opt_fields="%2C".join(API_OPT_FIELDS)
                ),
                cookies={'SERVER_ID': server_id},
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )

        process_feed.apply_async.assert_not_called()

    def test_handle_server_cookie_error(self):

        with patch("crawler.tasks.requests") as requests_mock:
            requests_mock.get.return_value = Mock(
                status_code=412,
                cookies=requests.utils.cookiejar_from_dict({"SERVER_ID": "f" * 32})
            )
            requests_mock.utils.dict_from_cookiejar = requests.utils.dict_from_cookiejar

            process_feed.retry = Mock(side_effect=Retry)
            with self.assertRaises(Retry):
                process_feed(cookies={"SERVER_ID": "1" * 32})

            process_feed.retry.assert_called_once_with(kwargs=dict(cookies={"SERVER_ID": "f" * 32}))

    def test_handle_feed_offset_error(self):

        with patch("crawler.tasks.requests") as requests_mock:
            requests_mock.get.return_value = Mock(
                status_code=404,
                json=Mock(return_value={
                    "status": "error",
                    "errors": [
                        {
                            "location": "params",
                            "name": "offset",
                            "description": "Offset expired/invalid"
                        }
                    ]
                }),
            )

            process_feed.retry = Mock(side_effect=Retry)
            with self.assertRaises(Retry):
                process_feed(offset="1" * 32, cookies={"SERVER_ID": "2" * 32})

            process_feed.retry.assert_called_once_with(kwargs=dict(cookies={"SERVER_ID": "2" * 32}))
