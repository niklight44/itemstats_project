.PHONY: up build migrate import test lint stop logs

build:
	docker compose build

up:
	docker compose up

migrate:
	docker compose run --rm web python manage.py migrate

import:
	docker compose run --rm web python manage.py import_items --source items/sample_data/sample.csv

test:
	docker compose run --rm web pytest -q

lint:
	docker compose run --rm web flake8

stop:
	docker compose down

logs:
	docker compose logs -f web
