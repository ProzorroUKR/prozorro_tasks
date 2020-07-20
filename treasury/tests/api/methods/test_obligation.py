from app.tests.base import BaseTestCase
from unittest.mock import patch
from http import HTTPStatus
from bson.objectid import ObjectId
from copy import deepcopy
from treasury.api.methods.obligation import Obligation
from treasury.tests.fixtures.obligation_data import (
    data_after_parse, data_after_parse_invalid_field_type
)


class ObligationTestCase(BaseTestCase):
    insert_one_db_mocked_data = {"status": HTTPStatus.CREATED, "data": ObjectId()}
    insert_one_db_access_error = {"status": HTTPStatus.SERVICE_UNAVAILABLE, "data": "MONGODB ACCESS ERROR"}
    parsed_data_mock = deepcopy(data_after_parse)
    parsed_data_with_field_error_mock = deepcopy(data_after_parse_invalid_field_type)

    @patch("treasury.api.methods.obligation.insert_one", return_value=insert_one_db_mocked_data)
    def test_fixture_request(self, db_insert_one_db_mock):
        with open("treasury/tests/fixtures/full_obligation_request.xml", "rb") as f:
            xml = f.read()

        response = self.client.post(
            '/treasury',
            data=xml,
            headers={"Content-Type": "application/xml"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            b'<?xml version="1.0" encoding="windows-1251"?>'
            b'<root>'
            b'<record id="124" result_code="0"/>'
            b'<record id="125" result_code="0"/>'
            b'</root>'
        )
        self.assertEqual(db_insert_one_db_mock.call_count, 2)

    @patch("treasury.api.methods.obligation.insert_one", return_value=insert_one_db_access_error)
    def test_access_error_db_response_status(self, db_insert_one_db_access_error_mock):
        with open("treasury/tests/fixtures/full_obligation_request.xml", "rb") as f:
            xml = f.read()

        response = self.client.post(
            '/treasury',
            data=xml,
            headers={"Content-Type": "application/xml"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            b'<?xml version="1.0" encoding="windows-1251"?>'
            b'<root>'
            b'<record id="124" result_code="30" result_text="MONGODB ACCESS ERROR"/>'
            b'<record id="125" result_code="30" result_text="MONGODB ACCESS ERROR"/>'
            b'</root>'
        )
        self.assertEqual(db_insert_one_db_access_error_mock.call_count, 2)

    @patch("treasury.api.methods.obligation.decode_data_from_base64", return_value="decoded_data")
    @patch("treasury.api.methods.obligation.XMLObligationDataParser.__init__", return_value=None)
    @patch("treasury.api.methods.obligation.XMLObligationDataParser.parse", return_value=parsed_data_mock)
    @patch("treasury.api.methods.obligation.insert_one", return_value=insert_one_db_mocked_data)
    def test_run_obligation(self, insert_one_db_mocked_data, parsed_data_mock, xml_parser_init_mock, decoded_data_mock):

        response = Obligation("encoded_data123456789", 12345).run()

        self.assertEqual(
            response,
             b'<?xml version="1.0" encoding="windows-1251"?>'
             b'<root>'
             b'<record id="12034" result_code="0"/>'
             b'<record id="12035" result_code="0"/>'
             b'</root>'
        )
        self.assertEqual(insert_one_db_mocked_data.call_count, 2)

    @patch("treasury.api.methods.obligation.decode_data_from_base64", return_value="decoded_data")
    @patch("treasury.api.methods.obligation.XMLObligationDataParser.__init__", return_value=None)
    @patch("treasury.api.methods.obligation.XMLObligationDataParser.parse",
           return_value=parsed_data_with_field_error_mock)
    @patch("treasury.api.methods.obligation.insert_one", return_value=insert_one_db_access_error)
    def test_run_obligation_record_with_failed_message(
            self, insert_one_db_access_error, parsed_data_with_error_mock, xml_parser_init_mock, decoded_data_mock):

        response = Obligation("encoded_data123456789", 12345).run()

        self.assertEqual(
            response,
            b'<?xml version="1.0" encoding="windows-1251"?>'
            b'<root>'
            b'<record id="12034" result_code="30" result_text="pmt_sum has incorrect data type"/>'
            b'<record id="12035" result_code="30" result_text="MONGODB ACCESS ERROR"/>'
            b'</root>'

        )
        self.assertEqual(insert_one_db_access_error.call_count, 1)
