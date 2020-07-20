from zeep import Client
from lxml import etree
from gzip import compress
import base64


def prepare_request(xml, message_id=1, method_name="PRTrans",
                    login="prozorrouser", password="111111",
                    should_compress=True, should_encode=True):
    client = Client("file://./treasury/tests/fixtures/wdsl.xml")  # use the local copy
    factory = client.type_factory("ns0")
    if should_compress:
        xml = compress(xml)
    if should_encode:
        xml = base64.b64encode(xml)
    message = factory.RequestMessage(
        UserLogin=login,
        UserPassword=password,
        MessageId=message_id,
        MethodName=method_name,
        Data=xml,
        DataSign=b"123",
    )
    message_node = client.create_message(client.service, 'SendRequest', message)
    return etree.tostring(message_node)
