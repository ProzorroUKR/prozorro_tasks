from treasury.api.parsers.obligation import XMLObligationDataParser
from environment_settings import TREASURY_OBLIGATION_COLLECTION
from treasury.storage import insert_one
from lxml import etree
from treasury.api.utils import decode_data_from_base64


class Obligation:
    def __init__(self, encoded_data, message_id):
        self.obligation_data = decode_data_from_base64(encoded_data)
        xml_obligation_data_parser = XMLObligationDataParser(self.obligation_data)
        self.parsed_data = xml_obligation_data_parser.parse()
        self.message_id = message_id

    def run(self):
        xml_response = ObligationXMLResponse()

        for entry in self.parsed_data:
            if not entry['failed_message']:
                response = insert_one(TREASURY_OBLIGATION_COLLECTION, entry)
                if response['status'] != 201:
                    entry['failed_message'].append(response['data'])
            xml_response.create_record(entry)
        response = xml_response.convert_to_string()

        return response


class ObligationXMLResponse:

    def __init__(self):
        self.root = etree.Element('root')

    def create_record(self, entry):

        if not entry['failed_message']:
            params = {'result_code': '0'}
        else:
            failed_message_str = ', '.join(entry['failed_message'])
            params = {'result_code': '30', 'result_text': failed_message_str}

        etree.SubElement(self.root, 'record', id=str(entry['recordId']), **params)

    def convert_to_string(self):
        return etree.tostring(self.root, encoding='windows-1251')
