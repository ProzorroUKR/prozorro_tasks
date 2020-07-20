from treasury.api.parsers.prtrans import XMLPRTransDataParser
from treasury.api.builders import XMLResponse
from treasury.api.utils import decode_data_from_base64, extract_data_from_zip
from treasury.tasks import process_transaction
from app.logging import getLogger

logger = getLogger()


class PRTrans:

    def __init__(self, encoded_data, message_id):
        _zip_data = decode_data_from_base64(encoded_data)
        self._data = extract_data_from_zip(_zip_data)
        xml_pr_trans_data_parser = XMLPRTransDataParser(self._data)
        self.parsed_data = xml_pr_trans_data_parser.parse()
        self.message_id = message_id

    def run(self):
        parsed_data = self.parsed_data

        process_transaction.delay(
            transactions_data=parsed_data,
            source=self._data.decode(errors="ignore"),
            message_id=self.message_id
        )
        logger.info(f"Sent to processing data: {parsed_data}")

        return XMLResponse(code="0", message="Sent to processing")
