from app.tests.base import BaseTestCase
from unittest.mock import patch
from treasury.tests.helpers import prepare_request
from http import HTTPStatus
from bson.objectid import ObjectId
from copy import deepcopy
from treasury.api.parsers.obligation import XMLObligationDataParser
from treasury.tests.fixtures.obligation_data import (
    data_before_parse, data_after_parse, data_before_parse_invalid_field_type, data_after_parse_invalid_field_type
)


class XMLObligationDataParserTestCase(BaseTestCase):
    insert_one_mocked_data = {"status": HTTPStatus.CREATED, "data": ObjectId()}

    @patch("treasury.api.methods.obligation.insert_one", return_value=insert_one_mocked_data)
    def test_required_fields(self, db_insert_one_mock):
        with open("treasury/tests/fixtures/full_obligation_request.xml", "rb") as f:
            xml = f.read()

        response = self.client.post(
            '/treasury',
            data=xml,
            headers={"Content-Type": "application/xml", "User-agent": "prozorro_tasks"}
        )
        self.assertEqual(
            response.data,
            b'<?xml version="1.0" encoding="windows-1251"?>'
            b'<root>'
            b'<record id="124" result_code="0"/>'
            b'<record id="125" result_code="0"/>'
            b'</root>'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(db_insert_one_mock.call_count, 2)

    @patch("treasury.api.methods.obligation.insert_one", return_value=insert_one_mocked_data)
    def test_missing_required_fields(self, db_insert_one_mock):

        xml = b"""<?xml version="1.0" encoding="windows-1251"?>
                <root method_name="Obligation">
                      <record id="124">
                        <pmt_date>2020-03-05T17:37:23+02:00</pmt_date>
                        <contractId>11C2E7D03AF649668BF9FFB1D0EF767D</contractId>
                        </record>
                    <record id="125">
                        <pmt_date>2020-05-05T17:46:38+02:00</pmt_date>
                        <pmt_status>-1</pmt_status>
                        <pmt_sum>1161960.00</pmt_sum>
                        <contractId>11C2E7D03AF649668BF9FFB1D0EF767D</contractId>
                    </record>
                </root>"""
        response = self.client.post(
            '/treasury',
            data=prepare_request(xml, method_name='Obligation', should_compress=False),
            headers={"Content-Type": "application/xml", "User-agent": "prozorro_tasks"}
        )
        self.assertEqual(
            response.data,
              b'<?xml version="1.0" encoding="windows-1251"?>'
              b'<root>'
              b'<record id="124" result_code="30" result_text="pmt_status is required, pmt_sum is required"/>'
              b'<record id="125" result_code="0"/>'
              b'</root>'
        )
        self.assertEqual(response.status_code, 200)
        db_insert_one_mock.assert_called_once()

    @patch("treasury.api.methods.obligation.insert_one", return_value=insert_one_mocked_data)
    def test_incorrect_fields_type(self, db_insert_one_mock):
        xml = b"""<?xml version="1.0" encoding="windows-1251"?>
                    <root method_name="Obligation">
                          <record id="124">
                            <pmt_date>2020-03-05T17:37:23+02:00</pmt_date>
                            <pmt_status>0</pmt_status>
                            <pmt_sum>1161960</pmt_sum>
                            <contractId>11C2E7D03AF649668BF9FFB1D0EF767D</contractId>
                            </record>
                        <record id="125">
                            <pmt_date>NOT DATE</pmt_date>
                            <pmt_status>1</pmt_status>
                            <pmt_sum>1161960.00</pmt_sum>
                            <contractId>11C2E7D03AF649668BF9FFB1D0EF767D</contractId>
                        </record>
                    </root>"""
        response = self.client.post(
            '/treasury',
            data=prepare_request(xml, method_name='Obligation', should_compress=False),
            headers={"Content-Type": "application/xml", "User-agent": "prozorro_tasks"}
        )
        self.assertEqual(
            response.data,
            b'<?xml version="1.0" encoding="windows-1251"?>'
            b'<root>'
            b'<record id="124" result_code="0"/>'
            b'<record id="125" result_code="30" '
            b'result_text="pmt_date has incorrect data type"/>'
            b'</root>'

        )
        self.assertEqual(response.status_code, 200)
        db_insert_one_mock.assert_called_once()

    @patch("treasury.api.methods.obligation.insert_one")
    def test_missing_required_record_id(self, db_insert_one_mock):

        xml = b"""<?xml version="1.0" encoding="windows-1251"?>
                <root method_name="Obligation">
                    <record>
                        <pmt_date>2020-03-05T17:37:23+02:00</pmt_date>
                        <pmt_status>0</pmt_status>
                        <pmt_sum>1161960</pmt_sum>
                        <contractId>11C2E7D03AF649668BF9FFB1D0EF767D</contractId>
                    </record>
                </root>"""
        response = self.client.post(
            '/treasury',
            data=prepare_request(xml, method_name='Obligation', should_compress=False),
            headers={"Content-Type": "application/xml", "User-agent": "prozorro_tasks"}
        )
        self.assertEqual(
            response.data,
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<Body><Response>'
            b'<ResultCode>30</ResultCode><ResultMessage>Can not find required record id</ResultMessage>'
            b'</Response></Body>'
        )
        self.assertEqual(response.status_code, 400)
        db_insert_one_mock.assert_not_called()

    @patch("treasury.api.methods.obligation.insert_one")
    def test_incorrect_record_id_type(self, db_insert_one_mock):
        xml = b"""<?xml version="1.0" encoding="windows-1251"?>
                    <root method_name="Obligation">
                        <record id="ABC_STRING001">
                            <pmt_date>2020-03-05T17:37:23+02:00</pmt_date>
                            <pmt_status>0</pmt_status>
                            <pmt_sum>1161960</pmt_sum>
                            <contractId>11C2E7D03AF649668BF9FFB1D0EF767D</contractId>
                        </record>
                    </root>"""
        response = self.client.post(
            '/treasury',
            data=prepare_request(xml, method_name='Obligation', should_compress=False),
            headers={"Content-Type": "application/xml", "User-agent": "prozorro_tasks"}
        )
        self.assertEqual(
            response.data,
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<Body><Response>'
            b'<ResultCode>30</ResultCode><ResultMessage>Record id has incorrect data type</ResultMessage>'
            b'</Response></Body>'
        )
        self.assertEqual(response.status_code, 400)
        db_insert_one_mock.assert_not_called()

    def test_parse(self):
        xml_obligation_data_parser = XMLObligationDataParser(data_before_parse)
        result = xml_obligation_data_parser.parse()
        expected = deepcopy(data_after_parse)
        self.assertEqual(result, expected)

    def test_parse_invalid_field_type(self):
        xml_obligation_data_parser = XMLObligationDataParser(data_before_parse_invalid_field_type)
        result = xml_obligation_data_parser.parse()
        expected = deepcopy(data_after_parse_invalid_field_type)
        self.assertEqual(result, expected)
