# syntax=docker/dockerfile:1

FROM python:3.10-slim-buster

ENV POETRY_VERSION=1.8.3 \
    POETRY_VIRTUALENVS_CREATE=false

# Install poetry
RUN pip install "poetry==$POETRY_VERSION"

# Copy project
WORKDIR /app
COPY . /app/

# Install project
RUN poetry install --no-interaction --no-ansi --all-extras --without dev,docs

COPY docker-entrypoint.sh .
ENTRYPOINT ["sh", "./docker-entrypoint.sh"]
CMD ["modpoll", "--version"]
