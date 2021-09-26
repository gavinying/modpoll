ARG PYTHON_TAG="3.6-slim-buster"
FROM python:$PYTHON_TAG
ARG APP_TAG="0.3.7"
RUN pip install modpoll==$APP_TAG
ENTRYPOINT ["modpoll"]
CMD ["--version"]
