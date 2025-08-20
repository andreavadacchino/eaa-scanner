.PHONY: generate validate

generate:
	./generate --all

validate:
	python3 tools/validate.py data/findings.csv

.PHONY: web
web:
	python3 webapp/app.py
