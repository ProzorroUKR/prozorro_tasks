from flask_restplus import reqparse, abort


class Argument(reqparse.Argument):

    def handle_validation_error(self, error, bundle_errors):
        '''
        Called when an error is raised while parsing. Aborts the request
        with a 400 status and an error message

        :param error: the error that was raised
        :param bool bundle_errors: do not abort when first error occurs, return a
            dict with the name of the argument and the error message to be
            bundled
        '''
        error_msg = str(error)
        errors = {self.name: error_msg}

        if bundle_errors:
            return ValueError(error), errors
        abort(400, 'Input payload validation failed', errors=errors)
