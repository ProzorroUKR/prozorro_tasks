from treasury.api.utils import decode_data_from_base64, extract_data_from_zip
from treasury.api.parsers.base import XMLParser
from dataclasses import dataclass


class XMLPRTransDataParser(XMLParser):
    """
    Parse Trans Data
    """
    def __init__(self, encoded_data):
        _compress_data = decode_data_from_base64(encoded_data)
        _data = extract_data_from_zip(_compress_data)
        super().__init__(_data)


@dataclass(init=False)
class TransFields(XMLPRTransDataParser):
    ref: str
    doc_sq: str
    doc_datd: str
    doc_nam_a: str
    doc_iban_a: str
    doc_nam_b: str
    doc_iban_b: str
    msrprd_date: str
    id_contract: str
    doc_status: str

    def import_id_contract(self, value):
        self.id_contract = value.lower()
