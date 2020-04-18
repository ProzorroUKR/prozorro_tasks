from flask import Request

from app.utils import generate_request_id


class RequestId(object):
    """
    It ensures to assign request ID for each HTTP request and set it to
    request environment. The request ID is also added to HTTP response.

    env_client_request_id = custom_env_client_request_id
    resp_header_client_request_id = custom-x-client-request-id
    env_request_id = custom_env_request_id
    resp_header_request_id = custom-x-request-id
    """
    def __init__(self, app,
                 env_client_request_id='X_CLIENT_REQUEST_ID',
                 resp_header_client_request_id='X-Client-Request-ID',
                 env_request_id='X_REQUEST_ID',
                 resp_header_request_id='X-Request-ID'):
        self.app = app
        self.env_client_request_id = env_client_request_id
        self.resp_header_client_request_id = resp_header_client_request_id
        self.env_request_id = env_request_id
        self.resp_header_request_id = resp_header_request_id

    def __call__(self, environ, start_response):
        req = Request(environ)
        client_request_id = None
        if self.resp_header_client_request_id in req.headers:
            client_request_id = req.headers[self.resp_header_client_request_id]
            req.environ[self.env_client_request_id] = client_request_id
        if self.resp_header_request_id in req.headers:
            req_id = req.headers[self.resp_header_request_id]
        else:
            req_id = generate_request_id()
        environ[self.env_request_id] = req_id

        def _start_response(status, response_headers, *args):
            if client_request_id:
                response_headers.append((self.resp_header_client_request_id, client_request_id))
            if self.resp_header_request_id not in dict(response_headers).keys():
                response_headers.append((self.resp_header_request_id, req_id))
            return start_response(status, response_headers, *args)

        return self.app(environ, _start_response)
