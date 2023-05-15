import requests
import io
import pathlib
import json
from app.logging import getLogger

from base64 import b64encode, b64decode

from environment_settings import (
    PUBLIC_API_HOST, API_VERSION,
    API_SIGN_HOST, API_SIGN_USER, API_SIGN_PASSWORD,
    NAZK_API_HOST, NAZK_API_INFO_URI,
    NAZK_PROZORRO_OPEN_CERTIFICATE_NAME
)
from app.utils import encode_to_base64_str, get_cert_base64

logger = getLogger()


def get_entity_data_from_nazk(request_data):
    encrypted_request_data = encrypt_data(request_data)
    encrypted_data_base64 = encode_to_base64_str(encrypted_request_data)
    certificate_base64 = get_base64_prozorro_open_cert()
    response_data = send_request_to_nazk(certificate_base64, encrypted_data_base64)

    # Valid test response in base64
    # response_data = "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"

    if response_data:
        _entity_info = decrypt_data(response_data)
        return _entity_info


def encrypt_data(data: dict) -> bytes:
    response = requests.post(
        url="{}/encrypt_nazk_data".format(API_SIGN_HOST),
        json=data,
        auth=(API_SIGN_USER, API_SIGN_PASSWORD),
    )
    if response.status_code != 200:
        print("ENCRYPT DATA FAILED")
        logger.warning("Encrypt data failed", extra={"MESSAGE_ID": "NAZK_ENCRYPT_DATA_EXCEPTION"})
    return response.content


def get_base64_prozorro_open_cert() -> str:
    try:
        return get_cert_base64(NAZK_PROZORRO_OPEN_CERTIFICATE_NAME)
    except FileNotFoundError:
        logger.warning(
            '{} file not found'.format(NAZK_PROZORRO_OPEN_CERTIFICATE_NAME),
            extra={"MESSAGE_ID": "NAZK_CERTIFICATE_NOT_FOUND_EXCEPTION"},
        )


def send_request_to_nazk(cert: str, content: str) -> str:
    response = requests.post(
        url="{host}/{uri}".format(host=NAZK_API_HOST, uri=NAZK_API_INFO_URI),
        json={"certificate": cert, "data": content}
    )
    if response.status_code != 200:
        logger.warning("Request to Nazk failed. Status: {}".format(response.status_code))
    else:
        return response.text


def decrypt_data(data: str) -> dict:
    response = requests.post(
        url="{}/decrypt_nazk_data".format(API_SIGN_HOST),
        json={"data": data},
        auth=(API_SIGN_USER, API_SIGN_PASSWORD),
    )
    if response.status_code != 200:
        logger.warning(
            "Decrypt data failed. Status {}".format(response.status_code),
            extra={"MESSAGE_ID": "NAZK_DECRYPT_DATA_EXCEPTION"},
        )
    else:
        res = json.loads(response.content)
        return res


if __name__ == "__main__":
    entity_data = get_entity_data_from_nazk({
        "entityType": "individual",
        "entityRegCode": "1111111111",
        "indLastName": "Тест",
        "indFirstName": "Тест",
        "indPatronymic": "Тест"
    })

    print(entity_data)
