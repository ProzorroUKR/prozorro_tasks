from flask_restx import fields, Model

from liqpay_int.examples import (
    EXAMPLE_RESPONSE_SUCCESS_STATUS,
    EXAMPLE_RESPONSE_ERROR_STATUS,
    EXAMPLE_RESPONSE_FAILURE_STATUS,
    EXAMPLE_RESPONSE_ERROR_MESSAGE,
    EXAMPLE_RESPONSE_FAILURE_MESSAGE,
)

model_response_success_fields = {
    "status": fields.String(default=EXAMPLE_RESPONSE_SUCCESS_STATUS, example=EXAMPLE_RESPONSE_SUCCESS_STATUS),
}

model_response_error_fields = {
    "status": fields.String(default=EXAMPLE_RESPONSE_ERROR_STATUS, example=EXAMPLE_RESPONSE_ERROR_STATUS),
    "message": fields.String(example=EXAMPLE_RESPONSE_ERROR_MESSAGE),
}

model_response_failure_fields = {
    "status": fields.String(default=EXAMPLE_RESPONSE_FAILURE_STATUS, example=EXAMPLE_RESPONSE_FAILURE_STATUS),
    "message": fields.String(example=EXAMPLE_RESPONSE_FAILURE_MESSAGE),
}
model_response_success = Model(
    "ResponseSuccess", model_response_success_fields
)

model_response_error = Model(
    "ResponseError", model_response_error_fields
)

model_response_failure = Model(
    "ResponseFailure", model_response_failure_fields
)
