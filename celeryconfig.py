from kombu import Queue
from environment_settings import TIMEZONE
from celery.schedules import crontab

task_acks_late = True
# Default: Disabled.
# Late ack means the task messages will be acknowledged after the task has been executed,
# not just before (the default behavior).

task_reject_on_worker_lost = True
# Default: Disabled.
# Even if task_acks_late is enabled, the worker will acknowledge tasks
# when the worker process executing them abruptly exits or is signaled (e.g., KILL/INT, etc).
# Setting this to true allows the message to be re-queued instead,
# so that the task will execute again by the same worker, or another worker.

broker_connection_max_retries = None
# Default: 100.
# Maximum number of retries before we give up re-establishing a connection to the AMQP broker.
# If this is set to 0 or None, we’ll retry forever.

# https://github.com/celery/celery/issues/5410
broker_transport_options = {'confirm_publish': True}

task_ignore_result = True

# Celery will automatically retry sending messages in the event of connection failure,
# and retry behavior can be configured – like how often to retry,
# or a maximum number of retries – or disabled all together.
retry_policy = {
    'max_retries': None,
    'interval_start': 0,
    'interval_step': 0.2,
    'interval_max': 0.2,
}

task_modules = [
    'crawler',
    'edr_bot',
    'fiscal_bot',
    'tasks_utils',
    'payments.tasks.push',
    'payments.tasks.feed',
    'treasury',
]

tasks_modules_deprecated = [
    'payments',
]

# Route tasks to different queues
# crawler.tasks -> crawler
# edr_bot -> edr_bot
# etc.

task_routes = ([
    ('{}.*'.format(module_name), {'queue': module_name})
    for module_name in task_modules
],)

task_queues = tuple(
    Queue(module_name)
    for module_name in task_modules
) + (
    Queue(module_name)
    for module_name in tasks_modules_deprecated
) + (
    Queue('celery',  routing_key=''),  # default
)


timezone = TIMEZONE
beat_schedule = {
    'request-org-catalog-every-day': {
        'task': 'treasury.tasks.request_org_catalog',
        'schedule': crontab(hour=6, minute=0),
    },
    'check-payments-status-every-hour': {
        'task': 'payments.tasks.check_payments_status',
        'schedule': crontab(minute=0),
    },
}
