from flask_restx import resource

class Resource(resource.Resource):
    dispatch_decorators = []

    def __init__(self, api=None, *args, **kwargs):
        self.api = api

    def dispatch_request(self, *args, **kwargs):
        meth = super(Resource, self).dispatch_request
        for decorator in self.dispatch_decorators:
            meth = decorator(meth)
        return meth(*args, **kwargs)
