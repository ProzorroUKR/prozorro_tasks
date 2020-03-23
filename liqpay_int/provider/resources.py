from flask_restx import Namespace, Resource

from app.auth import ip_group_required
from celery_worker.celery import app as celery_app
from liqpay_int.provider.models import model_payment
from liqpay_int.responses import model_response_success

api = Namespace(
    'provider',
    description='Provider related operations.',
    path='/'
)

api.models[model_payment.name] = model_payment

api.models[model_response_success.name] = model_response_success


class PushResource(Resource):

    method_decorators = [ip_group_required("payment_providers")]

    @api.marshal_with(model_response_success, code=200)
    @api.expect(model_payment, validate=True)
    def post(self):
        celery_app.send_task('payments.process_payment', kwargs=dict(
            payment_data=api.payload
        ))
        return {"status": "success"}


api.add_resource(PushResource, '/push')
