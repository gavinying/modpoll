ARG PYTHON_TAG="3.6-slim-buster"
FROM python:$PYTHON_TAG
ARG APP_TAG="0.4.1"
WORKDIR /app

RUN pip install modpoll==$APP_TAG

COPY docker-entrypoint.sh .
ENTRYPOINT ["sh", "./docker-entrypoint.sh"]
CMD "modpoll --version"
