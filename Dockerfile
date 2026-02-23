FROM python:3.8-alpine3.20

RUN apk --no-cache add gcc build-base git libxml2-dev libxslt-dev

# Add user
RUN addgroup -g 10000 user && \
    adduser -S -u 10000 -G user -h /app user

# Set app home
ENV APP_HOME=/app
WORKDIR ${APP_HOME}

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.4 /uv /uvx /bin/

ARG UV_EXTRA_ARGS="--no-dev"

# Install dependencies
COPY pyproject.toml uv.lock ${APP_HOME}/
RUN uv sync --frozen --no-cache  ${UV_EXTRA_ARGS} --compile-bytecode

# Copy the rest of the application
COPY ./ ${APP_HOME}/

# Set the virtualenv
ENV VIRTUAL_ENV=${APP_HOME}/.venv
ENV PATH=${APP_HOME}/.venv/bin:$PATH
ENV PATH=${APP_HOME}:$PATH

# Set permissions
RUN chown -R user:user ${APP_HOME}
USER user
