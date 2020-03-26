from __future__ import absolute_import
from environment_settings import CELERY_BROKER_URL, SENTRY_DSN, SENTRY_ENVIRONMENT
from celery import Celery
from celery.signals import after_setup_logger, after_setup_task_logger
from pythonjsonlogger import jsonlogger
import celeryconfig

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration

if SENTRY_DSN:
    sentry_sdk.init(dsn=SENTRY_DSN, environment=SENTRY_ENVIRONMENT, integrations=[CeleryIntegration()])

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
                extra = dict(
                    TASK_ID=request.id,
                    TASK_NAME=task.name,
                    TASK_ARGS=request.args,
                    TASK_KWARGS=request.kwargs,
                    TASK_RETRIES=request.retries,
                )
                return extra
            self.get_task_extra = get_task_extra

    def format(self, record):
        task_extra = self.get_task_extra()
        record.__dict__.update(task_extra)
        return super().format(record)


@after_setup_logger.connect
@after_setup_task_logger.connect
def setup_loggers(logger, *args, **kwargs):
    formatter = TaskJsonFormatter(
        '%(levelname)s %(asctime)s %(module)s %(process)d '
        '%(message)s %(pathname)s $(lineno)d $(funcName)s'
    )
    for handler in logger.handlers:
        handler.setFormatter(formatter)
