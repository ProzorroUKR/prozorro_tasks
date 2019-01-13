from __future__ import absolute_import
from environment_settings import CELERY_BROKER_URL
from celery import Celery
import celeryconfig

app = Celery(
    'celery_worker',
    broker=CELERY_BROKER_URL,
    include=[
        'crawler.tasks',
        'edr_bot.tasks'
    ],
)
app.config_from_object(celeryconfig)
