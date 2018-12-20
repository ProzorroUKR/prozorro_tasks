from __future__ import absolute_import
from celery import Celery
import celeryconfig


app = Celery('celery_worker',
             broker='amqp://admin:mypass@rabbit:5672',
             # backend='rpc://',
             include=['celery_worker.tasks', 'crawler.tasks'],
             )
# app.config_from_object(celeryconfig)
