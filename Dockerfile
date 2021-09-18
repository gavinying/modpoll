FROM python:3.6-slim-buster
RUN pip install modpoll
CMD modpoll --help
