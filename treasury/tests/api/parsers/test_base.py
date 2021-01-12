from app.tests.base import BaseTestCase
from unittest.mock import patch
from treasury.tests.helpers import prepare_request


class BaseParserTestCase(BaseTestCase):
    @patch("treasury.tasks.process_transaction")
    def test_invalid_xml(self, process_transaction_mock):
        xml = b"<test>Hello, xml!<test>"
        response = self.client.post(
            '/treasury',
            data=prepare_request(xml),
            headers={"Content-Type": "application/xml", "User-agent": "prozorro_tasks"}
        )
        self.assertEqual(
            response.data,
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b"<Body><Response>"
            b"<ResultCode>80</ResultCode>"
            b"<ResultMessage>Invalid request xml: EndTag: '&lt;/' not found, line 1,"
            b" column 24 (&lt;string&gt;, line 1)</ResultMessage>"
            b"</Response></Body>"
        )
        self.assertEqual(response.status_code, 400)
        process_transaction_mock.assert_not_called()

    @patch("treasury.tasks.process_transaction")
    def test_invalid_bas64(self, process_transaction_mock):
        xml = b"abc"
        response = self.client.post(
            '/treasury',
            data=prepare_request(xml, should_encode=False, should_compress=False),
            headers={"Content-Type": "application/xml", "User-agent": "prozorro_tasks"}
        )
        self.assertEqual(
            response.data,
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<Body><Response>'
            b'<ResultCode>80</ResultCode>'
            b'<ResultMessage>Data base64 error: Incorrect padding</ResultMessage>'
            b'</Response></Body>'
        )
        self.assertEqual(response.status_code, 400)
        process_transaction_mock.assert_not_called()
