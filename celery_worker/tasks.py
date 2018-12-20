from .celery import app
from celery.utils.log import get_task_logger

# TODO: read this https://celery.readthedocs.io/en/latest/userguide/tasks.html

logger = get_task_logger(__name__)


@app.task(bind=True)
def echo_task(self, *args, **kwargs):
    logger.info("Run task {} {} {}".format(self.request.id, args, kwargs))
