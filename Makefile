.IGNORE: clean
.PHONY: all install lint format test tests clean run-kinto need-kinto-running serve-attachments

all: install

install:
	uv sync --all-extras

need-kinto-running:
	@curl http://localhost:8888/v0/ 2>/dev/null 1>&2 || (echo "Run 'make run-kinto' before starting tests." && exit 1)

run-kinto:
	uv run kinto migrate --ini tests/kinto.ini
	uv run kinto start --ini tests/kinto.ini

serve-attachments:
	uv run python -m http.server --directory /tmp/server/attachments 9999

test: tests
tests: install need-kinto-running
	uv run pytest --cov-report term-missing --cov-fail-under 95 --cov kinto_wizard

lint: install
	uv run ruff check src tests
	uv run ruff format --check src tests

format:
	uv run ruff check --fix src tests
	uv run ruff format src tests

clean:
	find src -name '__pycache__' -type d -exec rm -fr {} \;
	find tests -name '__pycache__' -type d -exec rm -fr {} \;
	rm -rf .coverage *.egg-info .pytest_cache .ruff_cache build dist
