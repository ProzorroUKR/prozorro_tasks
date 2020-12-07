from environment_settings import PUBLIC_API_HOST, API_VERSION
from crawler.settings import (
    API_LIMIT, TENDER_OPT_FIELDS, CONNECT_TIMEOUT, READ_TIMEOUT,
    FEED_URL_TEMPLATE, WAIT_MORE_RESULTS_COUNTDOWN
)
from unittest.mock import patch, Mock, call
from celery.exceptions import Retry
from crawler.tasks import process_feed
import unittest
import requests


@patch('celery_worker.locks.get_mongodb_collection', Mock(return_value=Mock(find_one=Mock(return_value=None))))
class ProcessTestCase(unittest.TestCase):

    def test_handle_connection_error(self):

        with patch("crawler.tasks.requests") as requests_mock:
            requests_mock.get.side_effect = requests.exceptions.ConnectionError()

            process_feed.retry = Mock(side_effect=Retry)
            with self.assertRaises(Retry):
                process_feed()

            process_feed.retry.assert_called_once_with(exc=requests_mock.get.side_effect)

    def test_handle_429_response(self):

        ret_aft = "13.4"
        with patch("crawler.tasks.requests") as requests_mock:
            requests_mock.get.return_value = Mock(
                status_code=429,
                headers={'Retry-After': ret_aft}
            )

            process_feed.retry = Mock(side_effect=Retry)
            with self.assertRaises(Retry):
                process_feed()

            process_feed.retry.assert_called_once_with(countdown=float(ret_aft))

    def test_start_crawler_few_results(self):
        server_id = "a" * 32
        cookies = {'SERVER_ID': server_id}
        with patch("crawler.tasks.requests") as requests_mock:
            requests_mock.get.return_value = Mock(
                status_code=200,
                cookies=Mock(get_dict=Mock(return_value=cookies)),
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
                    resource="tenders",
                ),
                params=dict(
                    feed="changes",
                    limit=API_LIMIT,
                    descending="1",
                    mode="_all_",
                    opt_fields=",".join(TENDER_OPT_FIELDS)
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
                        'resource': 'tenders',
                        'mode': '_all_',
                        'offset': 1,
                        'cookies': {'SERVER_ID': server_id},
                    }
                ),
            ],
            msg="Only forward crawling since len(data) < API_LIMIT"
        )

    def test_start_crawler(self):
        server_id = "a" * 32
        cookies = {'SERVER_ID': server_id}
        with patch("crawler.tasks.requests") as requests_mock:
            requests_mock.get.return_value = Mock(
                status_code=200,
                cookies=Mock(get_dict=Mock(return_value=cookies)),
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
                    resource="tenders",
                ),
                params=dict(
                    feed="changes",
                    limit=API_LIMIT,
                    descending="1",
                    mode="_all_",
                    opt_fields=",".join(TENDER_OPT_FIELDS)
                ),
                cookies={},
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )

        self.assertEqual(
            process_feed.apply_async.call_args_list,
            [
                call(
                    kwargs={
                        'resource': 'tenders',
                        'mode': '_all_',
                        'offset': -1,
                        'descending': '1',
                        'cookies': {'SERVER_ID': server_id}
                    }
                ),
                call(
                    countdown=60,
                    kwargs={
                        'resource': 'tenders',
                        'mode': '_all_',
                        'offset': 1,
                        'cookies': {'SERVER_ID': server_id},
                    }
                ),
            ],
            msg="Both forward and backward crawling"
        )

    def test_start_test_crawler(self):
        server_id = "a" * 32
        cookies = {'SERVER_ID': server_id}
        with patch("crawler.tasks.requests") as requests_mock:
            requests_mock.get.return_value = Mock(
                status_code=200,
                cookies=Mock(get_dict=Mock(return_value=cookies)),
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
            process_feed(mode="test")

            requests_mock.get.assert_called_once_with(
                FEED_URL_TEMPLATE.format(
                    host=PUBLIC_API_HOST,
                    version=API_VERSION,
                    resource="tenders",
                ),
                params=dict(
                    feed="changes",
                    limit=API_LIMIT,
                    descending="1",
                    mode="test",
                    opt_fields=",".join(TENDER_OPT_FIELDS)
                ),
                cookies={},
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )

        self.assertEqual(
            process_feed.apply_async.call_args_list,
            [
                call(
                    kwargs={
                        'resource': 'tenders',
                        'mode': 'test',
                        'offset': -1,
                        'descending': '1',
                        'cookies': {'SERVER_ID': server_id}
                    }
                ),
                call(
                    countdown=60,
                    kwargs={
                        'resource': 'tenders',
                        'mode': 'test',
                        'offset': 1,
                        'cookies': {'SERVER_ID': server_id},
                    }
                ),
            ],
            msg="Both forward and backward crawling"
        )

    def test_start_crawler_on_empty_feed(self):
        server_id = "a" * 32
        cookies = {'SERVER_ID': server_id}
        with patch("crawler.tasks.requests") as requests_mock:
            requests_mock.get.return_value = Mock(
                status_code=200,
                cookies=Mock(get_dict=Mock(return_value=cookies)),
                json=Mock(return_value={
                    'data': [],
                    'next_page': {
                        'offset': ""
                    }
                }),
            )
            process_feed.apply_async = Mock()
            process_feed()

            requests_mock.get.assert_called_once_with(
                FEED_URL_TEMPLATE.format(
                    host=PUBLIC_API_HOST,
                    version=API_VERSION,
                    resource="tenders",
                ),
                params=dict(
                    feed="changes",
                    limit=API_LIMIT,
                    descending="1",
                    mode="_all_",
                    opt_fields=",".join(TENDER_OPT_FIELDS)
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
                        'resource': 'tenders',
                        'mode': '_all_',
                        'cookies': {'SERVER_ID': server_id},
                        'try_count': 1,
                    }
                ),
            ],
            msg="Only forward crawling after initialization on empty feed response"
        )

    def test_proceed_empty_forward_crawler(self):
        server_id = "a" * 32
        cookies = {'SERVER_ID': server_id}
        with patch("crawler.tasks.requests") as requests_mock:
            requests_mock.get.return_value = Mock(
                status_code=200,
                json=Mock(return_value={
                    'data': [],
                    'next_page': {
                        'offset': ''
                    },
                }),
                cookies=Mock(get_dict=Mock(return_value=cookies)),
            )
            process_feed.apply_async = Mock()
            process_feed(offset='', try_count=1, cookies=cookies)

            requests_mock.get.assert_called_once_with(
                FEED_URL_TEMPLATE.format(
                    host=PUBLIC_API_HOST,
                    version=API_VERSION,
                    resource="tenders",
                ),
                params=dict(
                    feed="changes",
                    descending="1",
                    mode="_all_",
                    limit=API_LIMIT,
                    opt_fields=",".join(TENDER_OPT_FIELDS)
                ),
                cookies={'SERVER_ID': server_id},
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )

        process_feed.apply_async.assert_called_once_with(
            countdown=60,
            kwargs={
                'resource': 'tenders',
                'mode': '_all_',
                'cookies': {'SERVER_ID': server_id},
                'try_count': 2,
            }
        )

    def test_empty_forward_crawler_found_many_results(self):
        server_id = "a" * 32
        cookies = {'SERVER_ID': server_id}
        with patch("crawler.tasks.requests") as requests_mock:
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
                        'offset': -1
                    },
                    'prev_page': {
                        'offset': 1
                    },
                }),
                cookies=Mock(get_dict=Mock(return_value=cookies)),
            )
            process_feed.apply_async = Mock()
            process_feed(offset='', try_count=12, cookies=cookies)

            requests_mock.get.assert_called_once_with(
                FEED_URL_TEMPLATE.format(
                    host=PUBLIC_API_HOST,
                    version=API_VERSION,
                    resource="tenders",
                ),
                params=dict(
                    feed="changes",
                    descending="1",
                    mode="_all_",
                    limit=API_LIMIT,
                    opt_fields=",".join(TENDER_OPT_FIELDS)
                ),
                cookies={'SERVER_ID': server_id},
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )

        self.assertEqual(
            process_feed.apply_async.call_args_list,
            [
                call(
                    kwargs={
                        'resource': 'tenders',
                        'mode': '_all_',
                        'offset': -1,
                        'descending': '1',
                        'cookies': {'SERVER_ID': server_id}
                    }
                ),
                call(
                    countdown=60,
                    kwargs={
                        'resource': 'tenders',
                        'mode': '_all_',
                        'offset': 1,
                        'cookies': {'SERVER_ID': server_id},
                    }
                ),
            ],
            msg="Both forward and backward crawling"
        )

    def test_proceed_forward_crawler(self):
        server_id = "a" * 32
        cookies = {'SERVER_ID': server_id}
        with patch("crawler.tasks.requests") as requests_mock:
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
                cookies=Mock(get_dict=Mock(return_value=cookies)),
            )
            process_feed.apply_async = Mock()
            process_feed(offset=1, cookies={'SERVER_ID': server_id})

            requests_mock.get.assert_called_once_with(
                FEED_URL_TEMPLATE.format(
                    host=PUBLIC_API_HOST,
                    version=API_VERSION,
                    resource="tenders",
                ),
                params=dict(
                    feed="changes",
                    offset=1,
                    mode="_all_",
                    limit=API_LIMIT,
                    opt_fields=",".join(TENDER_OPT_FIELDS)
                ),
                cookies={'SERVER_ID': server_id},
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )

        process_feed.apply_async.assert_called_once_with(
            kwargs={
                'resource': 'tenders',
                'mode': '_all_',
                'offset': 2,
                'cookies': {'SERVER_ID': server_id}
            }
        )

    def test_proceed_forward_crawler_few_results(self):
        server_id = "a" * 32
        cookies = {'SERVER_ID': server_id}
        with patch("crawler.tasks.requests") as requests_mock:
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
                cookies=Mock(get_dict=Mock(return_value=cookies)),
            )
            process_feed.apply_async = Mock()
            process_feed(offset=1, cookies=cookies)

            requests_mock.get.assert_called_once_with(
                FEED_URL_TEMPLATE.format(
                    host=PUBLIC_API_HOST,
                    version=API_VERSION,
                    resource="tenders",
                ),
                params=dict(
                    feed="changes",
                    offset=1,
                    mode="_all_",
                    limit=API_LIMIT,
                    opt_fields=",".join(TENDER_OPT_FIELDS)
                ),
                cookies={'SERVER_ID': server_id},
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )

        process_feed.apply_async.assert_called_once_with(
            kwargs={
                'resource': 'tenders',
                'mode': '_all_',
                'offset': 2,
                'cookies': {'SERVER_ID': server_id}
            },
            countdown=WAIT_MORE_RESULTS_COUNTDOWN
        )

    def test_proceed_backward_crawler(self):
        server_id = "a" * 32
        cookies = {'SERVER_ID': server_id}
        with patch("crawler.tasks.requests") as requests_mock:
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
                cookies=Mock(get_dict=Mock(return_value=cookies)),
            )
            process_feed.apply_async = Mock()
            process_feed(offset=-1, descending=1, cookies=cookies)

            requests_mock.get.assert_called_once_with(
                FEED_URL_TEMPLATE.format(
                    host=PUBLIC_API_HOST,
                    version=API_VERSION,
                    resource="tenders",
                ),
                params=dict(
                    feed="changes",
                    descending=1,
                    offset=-1,
                    mode="_all_",
                    limit=API_LIMIT,
                    opt_fields=",".join(TENDER_OPT_FIELDS)
                ),
                cookies={'SERVER_ID': server_id},
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )

        process_feed.apply_async.assert_called_once_with(
            kwargs={
                'resource': 'tenders',
                'mode': '_all_',
                'offset': -2,
                'descending': 1,
                'cookies': {'SERVER_ID': server_id}
            }
        )

    def test_proceed_backward_crawler_few_results(self):
        server_id = "a" * 32
        cookies = {'SERVER_ID': server_id}
        with patch("crawler.tasks.requests") as requests_mock:
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
                cookies=Mock(get_dict=Mock(return_value=cookies)),
            )
            process_feed.apply_async = Mock()
            process_feed(offset=-1, descending=1, cookies=cookies)

            requests_mock.get.assert_called_once_with(
                FEED_URL_TEMPLATE.format(
                    host=PUBLIC_API_HOST,
                    version=API_VERSION,
                    resource="tenders",
                ),
                params=dict(
                    feed="changes",
                    descending=1,
                    offset=-1,
                    mode="_all_",
                    limit=API_LIMIT,
                    opt_fields=",".join(TENDER_OPT_FIELDS)
                ),
                cookies={'SERVER_ID': server_id},
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )

        process_feed.apply_async.assert_not_called()

    def test_handle_server_cookie_error(self):
        cookies = {"SERVER_ID": "f" * 32}
        with patch("crawler.tasks.requests") as requests_mock:
            requests_mock.get.return_value = Mock(
                status_code=412,
                cookies=Mock(get_dict=Mock(return_value=cookies)),
            )

            process_feed.retry = Mock(side_effect=Retry)
            with self.assertRaises(Retry):
                process_feed(cookies={"SERVER_ID": "1" * 32})

            process_feed.retry.assert_called_once_with(kwargs=dict(cookies=cookies))

    def test_handle_feed_offset_error(self):
        cookies = {"SERVER_ID": "2" * 32}
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
                process_feed(offset="1" * 32, cookies=cookies)

            process_feed.retry.assert_called_once_with(kwargs=dict(cookies=cookies))
