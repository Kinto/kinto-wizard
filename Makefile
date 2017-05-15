SERVER_CONFIG = tests/kinto.ini
VIRTUALENV = virtualenv
VENV := $(shell echo $${VIRTUAL_ENV-.venv})
PYTHON = $(VENV)/bin/python
DEV_STAMP = $(VENV)/.dev_env_installed.stamp
INSTALL_STAMP = $(VENV)/.install.stamp
TEMPDIR := $(shell mktemp -d)

.PHONY: all install migrate runkinto virtualenv tests

OBJECTS = .venv .coverage

all: install
install: $(INSTALL_STAMP)
$(INSTALL_STAMP): $(PYTHON) setup.py
	$(VENV)/bin/pip install -U pip
	$(VENV)/bin/pip install -Ue .
	touch $(INSTALL_STAMP)

$(VENV)/bin/kinto: virtualenv
	$(VENV)/bin/pip install -U kinto
install-kinto: $(VENV)/bin/kinto

install-dev: $(INSTALL_STAMP) $(DEV_STAMP)
$(DEV_STAMP): $(PYTHON) dev-requirements.txt
	$(VENV)/bin/pip install -r dev-requirements.txt
	touch $(DEV_STAMP)

virtualenv: $(PYTHON)
$(PYTHON):
	$(VIRTUALENV) $(VENV)

migrate:
	$(VENV)/bin/kinto migrate --ini $(SERVER_CONFIG)

$(SERVER_CONFIG):
	$(VENV)/bin/kinto init --ini $(SERVER_CONFIG) --backend=memory

runkinto: install-kinto $(SERVER_CONFIG) migrate
	$(VENV)/bin/kinto start --ini $(SERVER_CONFIG)

build-requirements:
	$(VIRTUALENV) $(TEMPDIR)
	$(TEMPDIR)/bin/pip install -U pip
	$(TEMPDIR)/bin/pip install -Ue .
	$(TEMPDIR)/bin/pip freeze | grep -v -- '^-e' > requirements.txt

tests:
	tox

clean:
	rm -fr build/ dist/ .tox .venv
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -type d | xargs rm -fr

tests-once: install-dev
	$(VENV)/bin/py.test --cov-report term-missing --cov-fail-under 100 --cov kinto_wizard
