# Short cuts for common operations

.PHONY: shell
shell:
	pipenv shell

.PHONY: install
install:
	pipenv install

.PHONY: gunicorn
gunicorn: install
	pipenv run gunicorn --reload --log-level=INFO -e FLASK_DEBUG=True -w 2 -b 127.0.0.1:5000 app:app

.PHONY: run
run: install
	pipenv run flask --debug --app=app:app run --port=5000

.PHONY: docker
docker:
	docker build . --tag "flipperzero-region-provisioning:latest"

.PHONY: docker_gunicorn
docker_gunicorn: docker
	docker run -it -p 5000:5000 --rm "flipperzero-region-provisioning:latest" 