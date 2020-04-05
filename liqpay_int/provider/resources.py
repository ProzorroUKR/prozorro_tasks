from celery.exceptions import TaskError
from requests.exceptions import RequestException

from app.auth import ip_group_required
from app.logging import getLogger
from liqpay_int.exceptions import ProzorroApiError
from liqpay_int.provider.models import model_payment
from liqpay_int.provider.namespaces import api
from liqpay_int.resources import Resource
from liqpay_int.responses import model_response_success
from payments.tasks import process_payment_data


logger = getLogger()


@api.route('/push', doc=False)
class PushResource(Resource):

    dispatch_decorators = [ip_group_required("payment_providers")]

    @api.marshal_with(model_response_success, code=200)
    @api.expect(model_payment, validate=True)
    def post(self):
        description = api.payload.get("description")
        amount = api.payload.get("amount")
        currency = api.payload.get("currency")
        extra = {"PAYMENT_DESCRIPTION": description}
        logger.info("Payment push received.", extra=extra)
        try:
            process_payment_data.apply_async(kwargs=dict(
                payment_data=dict(
                    description=description,
                    amount=amount,
                    currency=currency,
                )
            ))
        except (TaskError, RequestException):
            logger.error("Payment processing task failed.", extra=extra)
            raise ProzorroApiError()
        return {"status": "success"}
