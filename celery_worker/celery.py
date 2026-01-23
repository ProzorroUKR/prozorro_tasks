from __future__ import absolute_import

from environment_settings import CELERY_BROKER_URL, SENTRY_DSN, SENTRY_ENVIRONMENT
from celery import Celery
from celery.signals import after_setup_logger, after_setup_task_logger, worker_init
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


@worker_init.connect
def declare_queues_on_startup(sender, **kwargs):
    """
    Автоматичне створення черг при старті воркера.

    Логіка:
    1. Перевіряє чи черга вже існує (passive declare)
    2. Якщо існує - використовує як є (не змінює тип)
    3. Якщо не існує - створює з типом залежно від версії RabbitMQ:
       - RabbitMQ 3.x: classic черги
       - RabbitMQ 4.x+: quorum черги

    Це дозволяє коду працювати на всіх середовищах без додаткових налаштувань:
    - Dev: створює нові черги з правильним типом
    - Staging/Prod: використовує існуючі черги як є
    """
    from amqp.exceptions import NotFound

    with sender.app.connection() as conn:
        conn.connect()

        props = conn.connection.server_properties
        version = props.get('version', b'0.0.0')
        if isinstance(version, bytes):
            version = version.decode()
        major = int(version.split('.')[0])

        if major >= 4:
            queue_args = {"x-queue-type": "quorum"}
        else:
            queue_args = {}

        queue_names = celeryconfig.task_modules + ['celery']
        channel = conn.channel()

        for queue_name in queue_names:
            try:
                channel.queue_declare(queue=queue_name, passive=True)
            except NotFound:
                channel = conn.channel()
                channel.queue_declare(
                    queue=queue_name,
                    durable=True,
                    auto_delete=False,
                    arguments=queue_args,
                )


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

                if task is None:
                    # TODO: investigate why this happens (CS-15631)
                    return {}

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
                    TASK_ARGS_STR=str(task_args),
                    TASK_KWARGS_STR=str(task_kwargs),
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
