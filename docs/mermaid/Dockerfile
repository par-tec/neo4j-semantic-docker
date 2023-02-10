FROM python:alpine

RUN mkdir /app
COPY . /app
WORKDIR /app
ENTRYPOINT ["python3"]
CMD ["-mhttp.server"]
