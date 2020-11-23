import shelve
import threading
from logging import getLogger

from celery.events import EventReceiver
from celery.events.state import State as EventsState

from celery_worker.celery import app as capp
from environment_settings import CELERY_UI_EVENTS_MAX_WORKERS, CELERY_UI_EVENTS_MAX_TASKS

logger = getLogger()


class Events(threading.Thread):
    def __init__(self, capp, **kwargs):
        threading.Thread.__init__(self)
        self.daemon = True

        self.capp = capp
        self.state = EventsState(**kwargs)

    def run(self):
        try_interval = 1
        while True:
            logger.info("Starting to capture events...")
            try:
                import celery
                try_interval *= 2
                with self.capp.connection() as conn:
                    recv = EventReceiver(conn, handlers={"*": self.on_event}, app=self.capp)
                    try_interval = 1
                    recv.capture(limit=None, timeout=None, wakeup=True)
            except Exception as e:
                logger.error(
                    "Failed to capture events: '%s', "
                    "trying again in %s seconds.",
                    e, try_interval
                )
                logger.debug(e, exc_info=True)

    def on_event(self, event):
        self.state.event(event)


events = Events(
    capp=capp,
    max_workers_in_memory=CELERY_UI_EVENTS_MAX_WORKERS,
    max_tasks_in_memory=CELERY_UI_EVENTS_MAX_TASKS,
)
