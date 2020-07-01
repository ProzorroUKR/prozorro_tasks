from flask import Response
from lxml import etree, builder


class XMLResponse(Response):
    def __init__(self, *args, **kwargs):
        code, message = kwargs.pop("code"), kwargs.pop("message")
        if None not in (code, message):
            response = build_response(code=code, message=message)
            args = (response, *args)
        super().__init__(*args, mimetype='text/xml', **kwargs)


def build_response(code="0", message=""):
    maker = builder.ElementMaker()
    xml = maker.Body(
        maker.Response(
            maker.ResultCode(code),
            maker.ResultMessage(message)
        )
    )
    doc_type = b'<?xml version="1.0" encoding="UTF-8"?>'
    return doc_type + etree.tostring(xml, xml_declaration=False)
