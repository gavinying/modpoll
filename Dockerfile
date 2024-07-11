# syntax=docker/dockerfile:1

FROM python:3.10-slim-buster

ENV POETRY_VERSION=1.8.3

# Install poetry and disable virtualenv creation
RUN pip install "poetry==$POETRY_VERSION"
RUN poetry config virtualenvs.create false

# Copy only requirements to cache them in docker layer
WORKDIR /app
COPY poetry.lock pyproject.toml README.md /app/
COPY modpoll /app/modpoll

# Project initialization:
RUN poetry install --no-interaction --no-ansi --all-extras --without dev,docs

CMD ["modpoll", "--version"]
