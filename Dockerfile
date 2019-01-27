FROM python:3
RUN mkdir /app
WORKDIR /app
ADD requirements.txt /app/
RUN pip install -r requirements.txt
ADD celery_worker /app/celery_worker
ADD crawler /app/crawler
ADD edr_bot /app/edr_bot
COPY environment_settings.py run_tasks.py celeryconfig.py /app/