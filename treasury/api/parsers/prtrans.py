from treasury.api.parsers.base import XMLParser
from dataclasses import dataclass, fields
from treasury.api.builders import XMLResponse
from collections import namedtuple
from flask import abort
from dateutil.parser import parse as date_parser


class XMLPRTransDataParser(XMLParser):
    """
    Parse Trans Data
    """

    RequiredField = namedtuple('RequiredField', 'f_name f_type')

    RECORD_FIELDS = (
        RequiredField('ref', str),
        RequiredField('doc_sq', float),
        RequiredField('doc_datd', lambda _iso_date: date_parser(_iso_date)),
        RequiredField('doc_nam_a', str),
        RequiredField('doc_iban_a', str),
        RequiredField('doc_nam_b', str),
        RequiredField('doc_iban_b', str),
        RequiredField('msrprd_date', lambda _iso_date: date_parser(_iso_date)),
        RequiredField('id_contract', str),
        RequiredField('doc_status', int),
    )

    def __init__(self, _data):
        super().__init__(_data)

    def parse(self):
        _parsed_data = []
        records_obj = self.tree_obj.findall("record")
        if not records_obj:
            abort(XMLResponse(code="80", message=f"Empty PRTrans Data xml", status=400))
        for record in records_obj:

            parsed_record = {}

            for field in self.RECORD_FIELDS:
                field_name = field.f_name
                element = record.find(f".//{field_name}", namespaces=self.namespaces)
                if element is None or not element.text:
                    abort(XMLResponse(code="30", message=f"'{field_name}' is required", status=400))

                try:
                    validated_value = field.f_type(element.text)  # try to convert element to required type
                except ValueError:
                    abort(XMLResponse(code="30", message=f'{field.f_name} has incorrect data type', status=400))
                else:
                    parsed_record[field.f_name] = validated_value

                    if field_name == "doc_status":
                        self.validate_doc_status_value(validated_value, field_name)

            _parsed_data.append(parsed_record)
        return _parsed_data

    @staticmethod
    def validate_doc_status_value(value, field_name):
        if value not in (0, -1):
            abort(XMLResponse(code="30", message=f"'{field_name}' should be 0 or -1", status=400))
