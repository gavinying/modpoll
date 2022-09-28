ARG PYTHON_TAG="3.8-slim-buster"
FROM python:$PYTHON_TAG
ARG APP_TAG="0.4.9"
WORKDIR /app

RUN pip install modpoll==$APP_TAG

COPY docker-entrypoint.sh .
ENTRYPOINT ["sh", "./docker-entrypoint.sh"]
CMD ["modpoll", "--version"]
