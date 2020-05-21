from treasury.documents import prepare_documents
from unittest.mock import patch, Mock, call
import base64
import unittest


class DocumentsTestCase(unittest.TestCase):

    @patch("treasury.documents.open")
    @patch("treasury.documents.ZipFile")
    @patch("treasury.documents.tempfile.TemporaryDirectory")
    @patch("treasury.documents.download_file")
    def test_get_collection(self, download_file_mock, tmp_dir_mock, zip_file_mock, open_mock):
        item = dict(documents=[
            dict(
                id="1",
                dateModified="12:30",
            ),
            dict(
                id="1",
                dateModified="16:02",
                url="http://phd-hub.com/file.mov"  # this will be downloaded
            ),
            dict(
                id="1",
                dateModified="06:30"
            ),
            dict(
                id="2",
                dateModified="",
                url="file_2_url"   # this will be downloaded
            ),
            dict(
                id="3",
                dateModified="",
                url="file_3_url"  # this will be downloaded
            ),
        ])
        download_file_mock.side_effect = [
            ("filename.xml", b"content 1"),
            ("filename", b"content 2"),
            ("filename", b"content 3"),
        ]

        tmp_dir_name = "/hello_tmp"
        tmp_dir_mock.return_value.__enter__.return_value = tmp_dir_name

        zip_file_content = b"<zip_file_content>"
        open_mock.return_value.__enter__.return_value.read.return_value = zip_file_content

        task = Mock()

        # run
        prepare_documents(task, item)

        # checks
        self.assertEqual(base64.b64decode(item["documents"]), zip_file_content)

        open_mock.assert_any_call('/hello_tmp/filename.xml', 'wb')  # saving first file
        open_mock.assert_any_call('/hello_tmp/filename', 'wb')  # saving second file
        open_mock.assert_any_call('/hello_tmp/filename(1)', 'wb')  # saving third file
        open_mock.return_value.__enter__.return_value.write.assert_has_calls(
            [call(b'content 1'),
             call(b'content 2'),
             call(b'content 3')]
        )
        open_mock.assert_any_call('/hello_tmp/spam.zip', 'rb')  # reading zip file contents

        # files were added to the archive
        zip_file_mock.return_value.__enter__.return_value.write.assert_has_calls(
            [call('/hello_tmp/filename.xml', 'filename.xml'),
             call('/hello_tmp/filename', 'filename'),
             call('/hello_tmp/filename(1)', 'filename(1)')]
        )




