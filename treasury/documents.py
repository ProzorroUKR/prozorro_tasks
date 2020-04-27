from tasks_utils.requests import download_file
from zipfile import ZipFile, ZIP_DEFLATED
import os.path
import tempfile
import base64


def prepare_documents(task, item):
    if "documents" in item:
        # get rid of prev versions of files
        documents = {}
        for d in item["documents"]:
            if d["id"] not in documents or d["dateModified"] > documents[d["id"]]["dateModified"]:
                documents[d["id"]] = d
        item["documents"] = documents.values()

        # replacing links with b64 of a zip file
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_file = "spam.zip"
            full_zip_file = os.path.join(tmp_dir, zip_file)
            with ZipFile(full_zip_file, "w", compression=ZIP_DEFLATED) as zip_file:
                file_names = {zip_file}
                for document in item["documents"]:
                    filename, content = download_file(task, document["url"])

                    # getting unique filename
                    index = 1
                    if "." in filename:
                        name, ext = filename.split(".", 1)
                        name_suffix = f".{ext}"
                    else:
                        name, name_suffix = filename, ""
                    while filename in file_names:
                        filename = f"{name}({index}){name_suffix}"
                        index += 1
                    file_names.add(filename)

                    # saving file
                    full_file_name = os.path.join(tmp_dir, filename)
                    with open(full_file_name, "wb") as f:
                        f.write(content)

                    # zipping file
                    zip_file.write(full_file_name, filename)

            # getting base64 of the whole zip file
            with open(full_zip_file, "rb") as f:
                b64_docs = base64.b64encode(f.read())

            # replacing docs
            item["documents"] = b64_docs.decode()
