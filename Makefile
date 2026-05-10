PYTHON ?= python

.PHONY: install lint test clean help

install:
$(PYTHON) -m pip install -e .[dev]

lint:
$(PYTHON) -m ruff check .

format:
$(PYTHON) -m ruff format .

test:
$(PYTHON) -m pytest

clean:
rm -rf .pytest_cache .ruff_cache build dist src/*.egg-info .x1371

help:
$(PYTHON) -m x1371.cli --help
