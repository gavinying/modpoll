ARG PYTHON_TAG="3.8-slim"
FROM python:$PYTHON_TAG
ARG APP_TAG="0.5.1"
WORKDIR /app

RUN pip3 install modpoll==$APP_TAG

COPY docker-entrypoint.sh .
ENTRYPOINT ["sh", "./docker-entrypoint.sh"]
CMD ["modpoll", "--version"]
