VENV := $(shell echo $${VIRTUAL_ENV-.venv})
PYTHON = $(VENV)/bin/python
INSTALL_STAMP = $(VENV)/.install.stamp

.PHONY: all
all: install

install: $(INSTALL_STAMP)
$(INSTALL_STAMP): $(PYTHON) pyproject.toml requirements.txt
	$(VENV)/bin/pip install -U pip
	$(VENV)/bin/pip install -r requirements.txt
	$(VENV)/bin/pip install -e ".[dev]"
	touch $(INSTALL_STAMP)

$(PYTHON):
	python3 -m venv $(VENV)

requirements.txt: requirements.in
	pip-compile

need-kinto-running:
	@curl http://localhost:8888/v0/ 2>/dev/null 1>&2 || (echo "Run 'make run-kinto' before starting tests." && exit 1)

run-kinto: install
	$(VENV)/bin/kinto migrate --ini tests/kinto.ini
	$(VENV)/bin/kinto start --ini tests/kinto.ini

.PHONY: tests
test: tests
tests: install need-kinto-running
	$(VENV)/bin/pytest --cov-report term-missing --cov-fail-under 95 --cov kinto_wizard

.PHONY: lint
lint: install
	$(VENV)/bin/ruff check src tests
	$(VENV)/bin/ruff format --check src tests

.PHONY: format
format: install
	$(VENV)/bin/ruff check --fix src tests
	$(VENV)/bin/ruff format src tests

.IGNORE: clean
clean:
	find src -name '__pycache__' -type d -exec rm -fr {} \;
	find tests -name '__pycache__' -type d -exec rm -fr {} \;
	rm -rf .venv .coverage *.egg-info .pytest_cache .ruff_cache build dist
