from flask import jsonify
from flask_restplus import Namespace, Resource

from app.auth import ip_group_required
from celery_worker.celery import app as celery_app
from liqpay_int.provider.parsers import parser_push


api = Namespace('provider', description='Provider related operations.', path='/')


class PushResource(Resource):

    method_decorators = [ip_group_required("payment_providers")]

    @api.expect(parser_push, validate=True)
    def post(self):
        celery_app.send_task('payments.process_payment', kwargs=dict(
            payment_data=parser_push.parse_args()
        ))
        return jsonify({"status": "success"})


api.add_resource(PushResource, '/push')
