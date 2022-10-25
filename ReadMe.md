# About

Flipper Zero FW build report analyzer backend

# Requirements

Docker or Python3 with pipenv module

# Development

You need to set the DATABASE_URI env variable to point to the db server, eg 
`DATABASE_URI=mysql://user_name:password@host.dev/amap_reports`.

- `make run` - to start flask development server
- `make gunicorn` - to start gunicorn development server
- `make docker` - build `firmware-report-server` and tag with `latest`
- `make docker_gunicorn` - build docker image and start service
- `make install` - to install requirements
- `make shell` - activate pipenv shell, but other make commands won't work in that shell

# Testing

`curl -v http://127.0.0.1:5000/api/v0/branches`

# Production

- `make docker` - build `firmware-report-server` and tag with `latest`
- Upload to container docker repository