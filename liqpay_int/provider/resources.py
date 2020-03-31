from celery.exceptions import TaskError
from requests.exceptions import RequestException

from app.auth import ip_group_required
from liqpay_int.exceptions import ProzorroApiError
from liqpay_int.provider.models import model_payment
from liqpay_int.provider.namespaces import api
from liqpay_int.resources import Resource
from liqpay_int.responses import model_response_success
from payments.tasks import process_payment


@api.route('/push', doc=False)
class PushResource(Resource):

    dispatch_decorators = [ip_group_required("payment_providers")]

    @api.marshal_with(model_response_success, code=200)
    @api.expect(model_payment, validate=True)
    def post(self):
        try:
            process_payment.apply_async(kwargs=dict(
                payment_data=api.payload
            ))
        except (TaskError, RequestException):
            raise ProzorroApiError()
        return {"status": "success"}
