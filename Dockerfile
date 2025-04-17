
FROM python:3.8
RUN groupadd -g 10000 user && \
    useradd -r -u 10000 -g user -d /app user
WORKDIR /app
ADD requirements.txt /app/
RUN pip install --upgrade setuptools
RUN pip install -r requirements.txt
COPY . /app
RUN chown -R user:user /app
USER user
