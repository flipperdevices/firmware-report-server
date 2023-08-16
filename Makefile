# Short cuts for common operations

.PHONY: shell
shell:
	pipenv shell

.PHONY: install
install:
	pipenv install

.PHONY: tests
tests: install
	pipenv run pytest tests -s

.PHONY: gunicorn
gunicorn: install
	pipenv run gunicorn --reload --log-level=INFO -e FLASK_DEBUG=True -w 2 -b 0.0.0.0:6754 app:app

.PHONY: run
run: install
	pipenv run flask --debug --app=app:app run --port=6754

.PHONY: docker
docker:
	docker build . --tag "firmware-report-server:latest"

.PHONY: docker_gunicorn
docker_gunicorn: docker
	docker run -it -p 6754:6754 --rm -e DATABASE_URI=${DATABASE_URI} "firmware-report-server:latest" 