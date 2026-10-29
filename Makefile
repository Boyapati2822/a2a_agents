lint:
	ruff check .
format-check:
	ruff format --check .
test:
	pytest -v