from flask import abort
from treasury.api.builders import XMLResponse
from collections import namedtuple
from dateutil.parser import parse as date_parser
from treasury.api.parsers.base import XMLParser


class XMLObligationDataParser(XMLParser):
    """
    Parse Obligation Data
    """

    RequiredField = namedtuple('RequiredField', 'f_name f_type')

    RECORD_FIELDS = (
        RequiredField('pmt_date', lambda _iso_date: date_parser(_iso_date)),
        RequiredField('pmt_status', int),
        RequiredField('pmt_sum', float),
        RequiredField('contractId', str)
    )
    namespaces = {}

    def parse(self):
        _parsed_data = []
        records_obj = self.tree_obj.findall("record")

        for record_obj in records_obj:
            record_id = record_obj.get("id")
            if not record_id:
                abort(XMLResponse(code="30", message=f"Can not find required record id", status=400))
            if not record_id.isnumeric():
                abort(XMLResponse(code="30", message=f"Record id has incorrect data type", status=400))

            parsed_record = {
                "recordId": int(record_id),
                "failed_message": []
            }

            for field in self.RECORD_FIELDS:
                element = record_obj.find(f".//{field.f_name}", namespaces=self.namespaces)
                if element is None or not element.text:
                    parsed_record["failed_message"].append(f'{field.f_name} is required')
                else:
                    try:
                        validated_value = field.f_type(element.text)  # try to convert element to required type
                    except ValueError:
                        parsed_record["failed_message"].append(f'{field.f_name} has incorrect data type')
                    else:
                        parsed_record[field.f_name] = validated_value
            _parsed_data.append(parsed_record)

        return _parsed_data
