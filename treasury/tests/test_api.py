from app.tests.base import BaseTestCase
from zeep import Client
from lxml import etree
from gzip import compress
from unittest.mock import patch
import base64


class TestCase(BaseTestCase):

    @patch("treasury.api.methods.save_transaction")
    def test_unicode_fixture(self, save_transaction_mock):
        self.maxDiff = None
        with open("treasury/tests/fixtures/PrTrans_unicode.xml", "rb") as f:
            xml = f.read()

        response = self.client.post(
            '/treasury',
            data=xml,
            headers={"Content-Type": "application/xml"}
        )
        self.assertEqual(
            response.data,
            b'<xml><Body><Response>'
            b'<ResultCode>0</ResultCode>'
            b'<ResultMessage>Sent to processing</ResultMessage>'
            b'</Response></Body></xml>'
        )
        save_transaction_mock.delay.assert_called_once_with(
            source='<?xml version="1.0" encoding="windows-1251"?><root method_name="PRTrans">'
                   '<record><ref>22</ref><doc_sq>11619.6</doc_sq>'
                   '<doc_datd>2020-03-11T00:00:00+03:00</doc_datd>'
                   '<doc_nam_a></doc_nam_a>'
                   '<doc_iban_a>UA678201720355110002000080850</doc_iban_a>'
                   '<doc_nam_b></doc_nam_b>'
                   '<doc_iban_b>UA098201720355179002000014715</doc_iban_b>'
                   '<msrprd_date>2020-03-11T00:00:00+03:00</msrprd_date>'
                   '<id_contract>11C2E7D03AF649668BF9FFB1D0EF767D</id_contract>'
                   '<doc_status>0</doc_status></record></root>',
            transaction={
                'contract_id': '11c2e7d03af649668bf9ffb1d0ef767d',
                'transaction_id': '22',
                'data': {
                    'date': '2020-03-11T00:00:00+03:00',
                    'value': {'amount': '11619.6'},
                    'payer': {'id': 'UA678201720355110002000080850', 'name': 'Тест'},
                    'payee': {'id': 'UA098201720355179002000014715',
                              'name': 'йцукенгшщзхїфівапролджєячсмитьбю'},
                    'status': '0'
                }
            }
        )

    @patch("treasury.api.methods.save_transaction")
    def test_fixture_request(self, save_transaction_mock):
        with open("treasury/tests/fixtures/PrTrans_id_181.xml", "rb") as f:
            xml = f.read()

        response = self.client.post(
            '/treasury',
            data=xml,
            headers={"Content-Type": "application/xml"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            b'<xml><Body><Response>'
            b'<ResultCode>0</ResultCode>'
            b'<ResultMessage>Sent to processing</ResultMessage>'
            b'</Response></Body></xml>'
        )
        save_transaction_mock.delay.assert_called_once_with(
            source='<?xml version="1.0" encoding="windows-1251"?><root method_name="PRTrans"><record><ref>2</ref><doc_sq>11619.6</doc_sq><doc_datd>2020-03-11T00:00:00+02:00</doc_datd><doc_nam_a>Test</doc_nam_a><doc_iban_a>UA678201720355110002000080850</doc_iban_a><doc_nam_b>Test</doc_nam_b><doc_iban_b>UA098201720355179002000014715</doc_iban_b><msrprd_date>2020-03-11T00:00:00+02:00</msrprd_date><id_contract>11C2E7D03AF649668BF9FFB1D0EF767D</id_contract><doc_status>0</doc_status></record><record><ref>2</ref><doc_sq>11619.6</doc_sq><doc_datd>2020-03-11T00:00:00+02:00</doc_datd><doc_nam_a>Test</doc_nam_a><doc_iban_a>UA678201720355110002000080850</doc_iban_a><doc_nam_b>Test</doc_nam_b><doc_iban_b>UA098201720355179002000014715</doc_iban_b><msrprd_date>2020-03-11T00:00:00+02:00</msrprd_date><id_contract>11C2E7D03AF649668BF9FFB1D0EF767D</id_contract><doc_status>-1</doc_status></record></root>',
            transaction=dict(
                contract_id='11c2e7d03af649668bf9ffb1d0ef767d',
                data={
                    'date': '2020-03-11T00:00:00+02:00',
                    'value': {'amount': '11619.6'},
                    'payer': {'id': 'UA678201720355110002000080850', 'name': 'Test'},
                    'payee': {'id': 'UA098201720355179002000014715', 'name': 'Test'},
                    'status': '0'
                },
                transaction_id='2'
            )
        )

    @staticmethod
    def prepare_request(xml, message_id=1, method_name="PRTrans",
                        login="prozorrouser", password="111111",
                        should_compress=True, should_encode=True):
        client = Client("file://./treasury/tests/fixtures/wdsl.xml")  # use the local copy
        factory = client.type_factory("ns0")
        if should_compress:
            xml = compress(xml)
        if should_encode:
            xml = base64.b64encode(xml)
        message = factory.RequestMessage(
            UserLogin=login,
            UserPassword=password,
            MessageId=message_id,
            MethodName=method_name,
            Data=xml,
            DataSign=b"",
        )
        message_node = client.create_message(client.service, 'SendRequest', message)
        return etree.tostring(message_node)

    @patch("treasury.api.methods.save_transaction")
    def test_required_fields(self, save_transaction_mock):
        xml = b"""<?xml version="1.0" encoding="windows-1251"?>
<root method_name="PRTrans">
  <record>
    <ref>1</ref>
    <doc_sq>18.44</doc_sq>
    <doc_datd>2020-03-11T00:00:00+02:00</doc_datd>
    <doc_nam_a>Test</doc_nam_a>
    <doc_iban_a>UA678201720355110002000080850</doc_iban_a>
    <doc_nam_b>Test</doc_nam_b>
    <doc_iban_b>UA098201720355179002000014715</doc_iban_b>
    <msrprd_date>2020-03-11T00:00:00+02:00</msrprd_date>
    <id_contract>11C2E7D03AF649668BF9FFB1D0EF767D</id_contract>
  </record>
</root>"""
        response = self.client.post(
            '/treasury',
            data=self.prepare_request(xml),
            headers={"Content-Type": "application/xml"}
        )
        self.assertEqual(
            response.data,
            b"<xml><Body><Response>"
            b"<ResultCode>30</ResultCode>"
            b"<ResultMessage>'doc_status' is required</ResultMessage>"
            b"</Response></Body></xml>"
        )
        self.assertEqual(response.status_code, 400)
        save_transaction_mock.assert_not_called()

    @patch("treasury.api.methods.save_transaction")
    def test_without_compressing(self, save_transaction_mock):
        xml = b"""<?xml version="1.0" encoding="windows-1251"?>
    <root method_name="PRTrans">
      <record>
        <ref>1</ref>
        <doc_sq>18.44</doc_sq>
        <doc_datd>2020-03-11T00:00:00+02:00</doc_datd>
        <doc_nam_a>Test</doc_nam_a>
        <doc_iban_a>UA678201720355110002000080850</doc_iban_a>
        <doc_nam_b>Test</doc_nam_b>
        <doc_iban_b>UA098201720355179002000014715</doc_iban_b>
        <msrprd_date>2020-03-11T00:00:00+02:00</msrprd_date>
        <id_contract>11C2E7D03AF649668BF9FFB1D0EF767D</id_contract>
        <doc_status>-1</doc_status>
      </record>
    </root>"""
        response = self.client.post(
            '/treasury',
            data=self.prepare_request(xml, should_compress=False),
            headers={"Content-Type": "application/xml"}
        )
        self.assertEqual(
            response.data,
            b'<xml><Body><Response>'
            b'<ResultCode>0</ResultCode>'
            b'<ResultMessage>Sent to processing</ResultMessage></Response></Body></xml>'
        )
        self.assertEqual(response.status_code, 200)
        save_transaction_mock.delay.assert_called_once()

    @patch("treasury.api.methods.save_transaction")
    def test_invalid_xml(self, save_transaction_mock):
        xml = b"<test>Hello, xml!<test>"
        response = self.client.post(
            '/treasury',
            data=self.prepare_request(xml),
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

    @patch("treasury.api.methods.save_transaction")
    def test_invalid_bas64(self, save_transaction_mock):
        xml = b"abc"
        response = self.client.post(
            '/treasury',
            data=self.prepare_request(xml, should_encode=False, should_compress=False),
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

    @patch("treasury.api.methods.save_transaction")
    def test_invalid_password(self, save_transaction_mock):
        response = self.client.post(
            '/treasury',
            data=self.prepare_request(b"", password="eee"),
            headers={"Content-Type": "application/xml"}
        )
        self.assertEqual(
            response.data,
            b'<xml><Body><Response>'
            b'<ResultCode>10</ResultCode>'
            b'<ResultMessage>Invalid login or password</ResultMessage></Response>'
            b'</Body></xml>'
        )
        self.assertEqual(response.status_code, 403)
        save_transaction_mock.assert_not_called()

    @patch("treasury.api.methods.save_transaction")
    def test_invalid_method(self, save_transaction_mock):
        response = self.client.post(
            '/treasury',
            data=self.prepare_request(b"", method_name="eee"),
            headers={"Content-Type": "application/xml"}
        )
        self.assertEqual(
            response.data,
            b'<xml><Body><Response>'
            b'<ResultCode>40</ResultCode>'
            b'<ResultMessage>Invalid method: eee</ResultMessage>'
            b'</Response></Body></xml>'
        )
        self.assertEqual(response.status_code, 400)
        save_transaction_mock.assert_not_called()
