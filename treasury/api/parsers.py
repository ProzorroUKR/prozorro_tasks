from app import app
from flask import abort
from treasury.api.builders import XMLResponse
from base64 import b64decode
from lxml import etree
from dataclasses import dataclass, fields
from gzip import decompress


class XMLParser:
    """
    Gets xml
    Returns an instance of data class with specified fields
    """
    namespaces = {}

    def __init__(self, data):
        self.data = data
        try:
            tree_obj = etree.fromstring(data)
        except Exception as e:
            err_msg = f"Invalid request xml: {e}"
            app.app.logger.warning(err_msg)
            abort(XMLResponse(code="80", message=err_msg, status=400))
        else:
            for field in fields(self):
                field_name = field.name
                element = tree_obj.find(f".//{field_name}", namespaces=self.namespaces)
                if element is None or not element.text:
                    abort(XMLResponse(code="30", message=f"'{field_name}' is required", status=400))

                try:
                    method = getattr(self, f"import_{field_name}")
                except AttributeError:
                    setattr(self, field_name, element.text)
                else:
                    method(element.text)


class XMLDataParse(XMLParser):
    """
    Extract xml from base64 encoded zip file
    """
    def __init__(self, data):
        try:
            data = b64decode(data)
        except Exception as e:
            err_msg = f"Data base64 error: {e}"
            app.app.logger.warning(err_msg)
            abort(XMLResponse(code="80", message=err_msg, status=400))
        try:
            data = decompress(data)
        except Exception as exc:
            app.app.logger.warning(f"Cannot decompress request data: {exc}")
        super().__init__(data)


@dataclass(init=False)
class RequestFields(XMLParser):
    namespaces = {None: 'https://www.unity-bars.com/ws'}

    MethodName: str
    UserLogin: str
    UserPassword: str
    MessageId: str
    Data: str


@dataclass(init=False)
class TransFields(XMLDataParse):
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


