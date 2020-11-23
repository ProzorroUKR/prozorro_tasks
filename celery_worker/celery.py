from __future__ import absolute_import

from environment_settings import CELERY_BROKER_URL, SENTRY_DSN, SENTRY_ENVIRONMENT
from celery import Celery
from celery.signals import after_setup_logger, after_setup_task_logger
from pythonjsonlogger import jsonlogger
from functools import wraps
from inspect import getfullargspec
import celeryconfig

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.flask import FlaskIntegration

if SENTRY_DSN:
    sentry_sdk.init(dsn=SENTRY_DSN, environment=SENTRY_ENVIRONMENT, integrations=[
        CeleryIntegration(),
        FlaskIntegration()
    ])

app = Celery(
    'celery_worker',
    broker=CELERY_BROKER_URL,
    backend='rpc',
    include=[
        "{}.tasks".format(module_name)
        for module_name in celeryconfig.task_modules
    ],
)
app.config_from_object(celeryconfig)


OMITTED_STR = "<omitted>"


class TaskJsonFormatter(jsonlogger.JsonFormatter):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            from celery._state import get_current_task
        except ImportError:
            self.get_task_extra = lambda: {}
        else:
            def get_task_extra():
                task = get_current_task()
                request = task.request

                indexes = getattr(request, "formatter_omit_indexes", [])
                task_args = [
                    value if index + 1 not in indexes else OMITTED_STR
                    for index, value in enumerate(request.args)
                ]

                names = getattr(request, "formatter_omit_names", [])
                task_kwargs = {
                    key: value if key not in names else OMITTED_STR
                    for key, value in request.kwargs.items()
                }

                extra = dict(
                    TASK_ID=request.id,
                    TASK_NAME=task.name,
                    TASK_ARGS=task_args,
                    TASK_KWARGS=task_kwargs,
                    TASK_RETRIES=request.retries,
                )
                return extra
            self.get_task_extra = get_task_extra

    def format(self, record):
        task_extra = self.get_task_extra()
        record.__dict__.update(task_extra)
        return super().format(record)


    @staticmethod
    def omit(names):
        """
        Decorator to omit task positional arguments and keyword arguments in logs.
        Listed positional arguments and keyword arguments wil be replaced with `<omitted>`.

        :param names: list of positional arguments and keyword arguments names
        :return:
        """
        def decorator(func):
            args = getfullargspec(func).args
            indexes = [args.index(name) for name in names if name in args]

            @wraps(func)
            def wrapper(self, *args, **kwargs):
                if hasattr(self, "request"):
                    setattr(self.request, "formatter_omit_indexes", indexes)
                    setattr(self.request, "formatter_omit_names", names)
                return func(self, *args, **kwargs)

            return wrapper

        return decorator


formatter = TaskJsonFormatter(
    '%(levelname)s %(asctime)s %(module)s %(process)d '
    '%(message)s %(pathname)s $(lineno)d $(funcName)s'
)


@after_setup_logger.connect
@after_setup_task_logger.connect
def setup_loggers(logger, *args, **kwargs):
    for handler in logger.handlers:
        handler.setFormatter(formatter)
