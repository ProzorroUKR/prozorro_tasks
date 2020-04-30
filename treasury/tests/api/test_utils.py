from app.tests.base import BaseTestCase
from treasury.api.utils import encode_data_to_base64, decode_data_from_base64, extract_data_from_zip
from gzip import compress


class DataEncodeDecodeTestCase(BaseTestCase):
    def test_run(self):
        data = b'some_data_123'
        encoded_data = encode_data_to_base64(data)
        self.assertEqual(encoded_data, b'c29tZV9kYXRhXzEyMw==')

        decoded_data = decode_data_from_base64(encoded_data)
        self.assertEqual(decoded_data, b'some_data_123')


class DataUnpackerTestCase(BaseTestCase):
    def test_run(self):
        data = b'some_data_123'
        compressed_data = compress(data)
        unpacked_data = extract_data_from_zip(compressed_data)
        self.assertEqual(unpacked_data, b'some_data_123')

        data_without_compress = b'data_without_compress'
        result = extract_data_from_zip(data_without_compress)
        self.assertEqual(result, data_without_compress)
