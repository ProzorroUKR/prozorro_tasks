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
    xml = maker.xml(
        maker.Body(
            maker.Response(
                maker.ResultCode(code),
                maker.ResultMessage(message)
            )
        )
    )
    return etree.tostring(xml)
