FROM python:3.11.9-bookworm

RUN DEBIAN_FRONTEND=noninteractive apt update && apt install -y libmariadb3 libmariadb-dev build-essential

ADD pyproject.toml /app/pyproject.toml
ADD poetry.lock /app/poetry.lock
WORKDIR /app
RUN python3 -m pip install jsonschema==4.17.3 poetry && poetry config virtualenvs.create false && poetry install

ADD app /app/app

MAINTAINER devops@flipperdevices.com
ENV WORKERS=1
ENV PORT=80
ENV FLASK_DEBUG=0
CMD poetry run gunicorn -w ${WORKERS} -b 0.0.0.0:${PORT} app:app

EXPOSE ${PORT}/tcp

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
	CMD curl --fail http://127.0.0.1:${PORT}/api/v0/ping || exit 1
