from app import app
from flask import abort
from treasury.api.builders import XMLResponse
from lxml import etree
from dataclasses import dataclass, fields


class XMLParser:
    """
    Gets xml
    Returns an instance of data class with specified fields
    """
    namespaces = {}

    def __init__(self, data):
        self.data = data
        try:
            self.tree_obj = etree.fromstring(data)
        except Exception as e:
            err_msg = f"Invalid request xml: {e}"
            app.app.logger.warning(err_msg)
            abort(XMLResponse(code="80", message=err_msg, status=400))

    def parse(self):
        for field in fields(self):
            field_name = field.name
            element = self.tree_obj.find(f".//{field_name}", namespaces=self.namespaces)
            if element is None or not element.text:
                abort(XMLResponse(code="30", message=f"'{field_name}' is required", status=400))

            try:
                method = getattr(self, f"import_{field_name}")
            except AttributeError:
                setattr(self, field_name, element.text)
            else:
                method(element.text)
        return self


@dataclass(init=False)
class RequestFields(XMLParser):
    namespaces = {None: 'https://www.unity-bars.com/ws'}

    MethodName: str
    UserLogin: str
    UserPassword: str
    MessageId: str
    Data: str
    DataSign: str
