.PHONY: all test build format check lint clean

all: test check

check: lint

lint:
	ruff check .
	ruff format . --check

format:
	@ruff check . --fix
	ruff format .

test:
	uv run pytest tests

build: clean
	uv build

clean:
	rm -rf .pytest_cache .ruff_cache dist build __pycache__ .mypy_cache .coverage htmlcov .coverage.* *.egg-info

publish: build
	uv publish
