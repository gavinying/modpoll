FROM python:3.6-slim-buster
RUN pip install modpoll
ENTRYPOINT ["modpoll"]
CMD ["--help"]
