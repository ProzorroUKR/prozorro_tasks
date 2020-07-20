from app.tests.base import BaseTestCase
from unittest.mock import patch
from treasury.tests.helpers import prepare_request
from treasury.api.parsers.prtrans import XMLPRTransDataParser
import datetime
from dateutil.tz import tzoffset


class PrtransTestCase(BaseTestCase):
    @patch("treasury.tasks.process_transaction")
    def test_required_fields(self, process_transaction_mock):
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
            data=prepare_request(xml),
            headers={"Content-Type": "application/xml"}
        )
        self.assertEqual(
            response.data,
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b"<Body><Response>"
            b"<ResultCode>30</ResultCode>"
            b"<ResultMessage>'doc_status' is required</ResultMessage>"
            b"</Response></Body>"
        )
        self.assertEqual(response.status_code, 400)
        process_transaction_mock.assert_not_called()

    def test_parse_transaction(self):
        xml = b"""<?xml version="1.0" encoding="windows-1251"?>
            <root method_name="PRTrans">
              <record>
                <ref>1</ref>
                <doc_sq>18.44</doc_sq>
                <doc_datd>2020-05-11T00:00:00+02:00</doc_datd>
                <doc_nam_a>Test</doc_nam_a>
                <doc_iban_a>UA678201720355110002000080850</doc_iban_a>
                <doc_nam_b>Test</doc_nam_b>
                <doc_iban_b>UA098201720355179002000014715</doc_iban_b>
                <msrprd_date>2020-03-11T00:00:00+02:00</msrprd_date>
                <id_contract>11C2E7D03AF649668BF9FFB1D0EF767D</id_contract>
                <doc_status>-1</doc_status>
              </record>
              <record>
                <ref>2</ref>
                <doc_sq>33.44</doc_sq>
                <doc_datd>2020-05-11T00:00:00+02:00</doc_datd>
                <doc_nam_a>Test2</doc_nam_a>
                <doc_iban_a>UA678201720355110002000080850</doc_iban_a>
                <doc_nam_b>Test</doc_nam_b>
                <doc_iban_b>UA098201720355179002000014715</doc_iban_b>
                <msrprd_date>2020-03-11T00:00:00+02:00</msrprd_date>
                <id_contract>22C2E7D03AF649668BF9FFB1D0EF767D</id_contract>
                <doc_status>0</doc_status>
              </record>
            </root>"""

        xml_parser = XMLPRTransDataParser(xml)
        result = xml_parser.parse()

        expected_result = [
            {
                'ref': '1',
                'doc_sq': 18.44,
                'doc_datd': datetime.datetime(2020, 5, 11, 0, 0, tzinfo=tzoffset(None, 7200)),
                'doc_nam_a': 'Test',
                'doc_iban_a': 'UA678201720355110002000080850',
                'doc_nam_b': 'Test',
                'doc_iban_b': 'UA098201720355179002000014715',
                'msrprd_date': datetime.datetime(2020, 3, 11, 0, 0, tzinfo=tzoffset(None, 7200)),
                'id_contract': '11C2E7D03AF649668BF9FFB1D0EF767D',
                'doc_status': -1
            },
            {
                'ref': '2',
                'doc_sq': 33.44,
                'doc_datd': datetime.datetime(2020, 5, 11, 0, 0, tzinfo=tzoffset(None, 7200)),
                'doc_nam_a': 'Test2',
                'doc_iban_a': 'UA678201720355110002000080850',
                'doc_nam_b': 'Test',
                'doc_iban_b': 'UA098201720355179002000014715',
                'msrprd_date': datetime.datetime(2020, 3, 11, 0, 0, tzinfo=tzoffset(None, 7200)),
                'id_contract': '22C2E7D03AF649668BF9FFB1D0EF767D',
                'doc_status': 0
            }
        ]

        self.assertEqual(result, expected_result)

    @patch("treasury.tasks.process_transaction")
    def test_parse_empty_transaction_xml(self, process_transaction_mock):
        xml = b"""<?xml version="1.0" encoding="windows-1251"?>
            <root method_name="PRTrans">
            </root>"""

        response = self.client.post(
            '/treasury',
            data=prepare_request(xml),
            headers={"Content-Type": "application/xml"}
        )

        self.assertEqual(
            response.data,
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b"<Body><Response>"
            b"<ResultCode>80</ResultCode>"
            b"<ResultMessage>Empty PRTrans Data xml</ResultMessage>"
            b"</Response></Body>"
        )
        self.assertEqual(response.status_code, 400)
        process_transaction_mock.assert_not_called()

    @patch("treasury.tasks.process_transaction")
    def test_valid_field_type(self, process_transaction_mock):
        xml = b"""<?xml version="1.0" encoding="windows-1251"?>
                <root method_name="PRTrans">
                  <record>
                    <ref>1</ref>
                    <doc_sq>aaaaaa_invalid</doc_sq>
                    <doc_datd>2020-05-11T00:00:00+02:00</doc_datd>
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
            data=prepare_request(xml),
            headers={"Content-Type": "application/xml"}
        )
        self.assertEqual(
            response.data,
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<Body><Response>'
            b'<ResultCode>30</ResultCode>'
            b'<ResultMessage>doc_sq has incorrect data type</ResultMessage>'
            b'</Response></Body>'

        )
        self.assertEqual(response.status_code, 400)
        process_transaction_mock.assert_not_called()

    @patch("treasury.tasks.process_transaction")
    def test_valid_doc_status_value(self, process_transaction_mock):
        xml = b"""<?xml version="1.0" encoding="windows-1251"?>
                    <root method_name="PRTrans">
                      <record>
                        <ref>1</ref>
                        <doc_sq>18.44</doc_sq>
                        <doc_datd>2020-05-11T00:00:00+02:00</doc_datd>
                        <doc_nam_a>Test</doc_nam_a>
                        <doc_iban_a>UA678201720355110002000080850</doc_iban_a>
                        <doc_nam_b>Test</doc_nam_b>
                        <doc_iban_b>UA098201720355179002000014715</doc_iban_b>
                        <msrprd_date>2020-03-11T00:00:00+02:00</msrprd_date>
                        <id_contract>11C2E7D03AF649668BF9FFB1D0EF767D</id_contract>
                        <doc_status>222222222</doc_status>
                      </record>
                    </root>"""
        response = self.client.post(
            '/treasury',
            data=prepare_request(xml),
            headers={"Content-Type": "application/xml"}
        )
        self.assertEqual(
            response.data,
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b"<Body><Response>"
            b"<ResultCode>30</ResultCode>"
            b"<ResultMessage>'doc_status' should be 0 or -1</ResultMessage>"
            b"</Response></Body>"

        )
        self.assertEqual(response.status_code, 400)
        process_transaction_mock.assert_not_called()
