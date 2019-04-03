FROM python:3
RUN mkdir /app
WORKDIR /app
ADD requirements.txt /app/
RUN pip install -r requirements.txt
COPY . /app
HEALTHCHECK --interval=60s --timeout=30s --retries=3 CMD python healthcheck.py