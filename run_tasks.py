#!/usr/local/bin/python
from celery_worker.celery import app

# import all task we want ot use
import crawler.tasks
import edr_bot.tasks


if __name__ == '__main__':
    while 1:
        print("Available tasks:", set(app.tasks.keys()))
        task_data = input(">")
        task_args = list(filter(None, [e.strip() for e in task_data.split()]))
        if task_args:
            task_name = task_args.pop(0)
            for key in app.tasks.keys():
                if task_name in key:
                    confirm = input("Do you want to run {} with args {}?(y/N):".format(key, task_args))
                    if confirm.lower() in ("y", "yes"):
                        app.tasks[key].delay()
                        break
