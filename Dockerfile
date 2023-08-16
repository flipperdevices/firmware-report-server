FROM python:3.11-alpine

MAINTAINER devops@flipperdevices.com

COPY Pipfile /Pipfile
COPY Pipfile.lock /Pipfile.lock

COPY app /app

RUN apk update \
    && apk add --virtual build-deps gcc python3-dev musl-dev \
    && apk add --no-cache mariadb-dev


RUN pip install pipenv
RUN pipenv install

ENV WORKERS=4
ENV PORT=6754
ENV FLASK_DEBUG=0

CMD pipenv run gunicorn -w ${WORKERS} -b 0.0.0.0:${PORT} app:app

EXPOSE ${PORT}/tcp

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
	CMD curl --fail http://127.0.0.1:${PORT}/api/v0/ping || exit 1