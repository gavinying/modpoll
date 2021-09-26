FROM python:3.8-slim-buster
ARG APP_TAG="0.3.6"
RUN pip install modpoll==$APP_TAG
ENTRYPOINT ["modpoll"]
CMD ["--version"]
