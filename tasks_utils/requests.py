import re


def get_filename_from_response(response):
    disposition = response.headers.get('content-disposition')
    if disposition:
        file_name = re.findall("filename=(.+)", disposition)
        if file_name:
            return file_name[0]
