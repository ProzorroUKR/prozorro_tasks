from app.tests.base import BaseTestCase
from unittest.mock import patch
from treasury.tests.helpers import prepare_request


class BaseParserTestCase(BaseTestCase):
    @patch("treasury.api.methods.prtrans.save_transaction")
    def test_invalid_xml(self, save_transaction_mock):
        xml = b"<test>Hello, xml!<test>"
        response = self.client.post(
            '/treasury',
            data=prepare_request(xml),
            headers={"Content-Type": "application/xml"}
        )
        self.assertEqual(
            response.data,
            b"<xml><Body><Response>"
            b"<ResultCode>80</ResultCode>"
            b"<ResultMessage>Invalid request xml: EndTag: '&lt;/' not found, line 1,"
            b" column 24 (&lt;string&gt;, line 1)</ResultMessage>"
            b"</Response></Body></xml>"
        )
        self.assertEqual(response.status_code, 400)
        save_transaction_mock.delay.assert_not_called()

    @patch("treasury.api.methods.prtrans.save_transaction")
    def test_invalid_bas64(self, save_transaction_mock):
        xml = b"abc"
        response = self.client.post(
            '/treasury',
            data=prepare_request(xml, should_encode=False, should_compress=False),
            headers={"Content-Type": "application/xml"}
        )
        self.assertEqual(
            response.data,
            b'<xml><Body><Response>'
            b'<ResultCode>80</ResultCode>'
            b'<ResultMessage>Data base64 error: Incorrect padding</ResultMessage>'
            b'</Response></Body></xml>'
        )
        self.assertEqual(response.status_code, 400)
        save_transaction_mock.delay.assert_not_called()
