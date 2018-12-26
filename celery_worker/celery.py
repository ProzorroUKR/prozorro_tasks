from __future__ import absolute_import
from celery import Celery
import celeryconfig

app = Celery(
    'celery_worker',
    broker='amqp://admin:mypass@rabbit:5672',
    include=[
        'crawler.tasks',
        'edr_bot.tasks'
    ],
)
app.config_from_object(celeryconfig)
