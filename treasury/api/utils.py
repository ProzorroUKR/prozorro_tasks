from app import app
from gzip import decompress
from base64 import b64decode, b64encode
from flask import abort
from treasury.api.builders import XMLResponse


def encode_data_to_base64(data):
    try:
        return b64encode(data)
    except Exception as e:
        err_msg = f"Data base64 error: {e}"
        app.app.logger.warning(err_msg)
        abort(XMLResponse(code="80", message=err_msg, status=400))


def decode_data_from_base64(data):
    try:
        return b64decode(data)
    except Exception as e:
        err_msg = f"Data base64 error: {e}"
        app.app.logger.warning(err_msg)
        abort(XMLResponse(code="80", message=err_msg, status=400))


def extract_data_from_zip(data):
    try:
        data = decompress(data)
    except Exception as exc:
        app.app.logger.warning(f"Cannot decompress request data: {exc}, Return raw data")
    return data
