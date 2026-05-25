.PHONY: all test test3 compile zipapp install clean doctor

PYTHON ?= python3
PREFIX ?= $(HOME)/.local
APP := telachat

all: compile test zipapp

compile:
	$(PYTHON) -m compileall -q src tests

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

test3:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

zipapp:
	mkdir -p dist
	$(PYTHON) -m zipapp src -m telachat:main -p "/usr/bin/env python3" -o dist/$(APP).pyz

install:
	mkdir -p "$(PREFIX)/bin"
	install -m 0755 bin/$(APP) "$(PREFIX)/bin/$(APP)"
	install -m 0755 bin/$(APP)-gtk "$(PREFIX)/bin/$(APP)-gtk"
	install -m 0755 bin/$(APP)-tk "$(PREFIX)/bin/$(APP)-tk"
	install -m 0755 bin/$(APP)-gui "$(PREFIX)/bin/$(APP)-gui"

doctor:
	PYTHONPATH=src $(PYTHON) -m telachat doctor

clean:
	rm -rf build dist *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
