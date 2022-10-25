FROM python:3.10-alpine

MAINTAINER devops@flipperdevices.com

COPY Pipfile /Pipfile
COPY Pipfile.lock /Pipfile.lock

COPY app /app

RUN apk add curl gcc musl-dev mariadb-connector-c-dev && pip install pipenv && pipenv install

ENV WORKERS=4
ENV PORT=6754
ENV FLASK_DEBUG=0

CMD pipenv run gunicorn -w ${WORKERS} -b 0.0.0.0:${PORT} app:app

EXPOSE ${PORT}/tcp

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
	CMD curl --fail http://127.0.0.1:${PORT}/api/v0/ping || exit 1