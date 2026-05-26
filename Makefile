.PHONY: all check test test3 compile zipapp linux-installer linux-installer-smoke linux-rpm install clean doctor

PYTHON ?= python3
PREFIX ?= $(HOME)/.local
APP := telachat
VERSION := $(shell $(PYTHON) -c 'import pathlib,tomllib; print(tomllib.loads(pathlib.Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["version"])')

all: compile test zipapp

check: compile test
	git diff --check

compile:
	$(PYTHON) -m compileall -q src tests packaging

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

test3:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

zipapp:
	mkdir -p dist
	$(PYTHON) -m zipapp src -p "/usr/bin/env python3" -o dist/$(APP).pyz

linux-installer: zipapp
	mkdir -p dist
	install -m 0755 packaging/linux/install-telachat.sh dist/$(APP)-install-$(VERSION).sh

linux-installer-smoke: linux-installer
	tmp_dir=$$(mktemp -d "$${TMPDIR:-/tmp}/$(APP)-install-smoke.XXXXXX"); \
	trap 'rm -rf "$$tmp_dir"' EXIT INT HUP TERM; \
	dist/$(APP)-install-$(VERSION).sh \
		--prefix "$$tmp_dir/prefix" \
		--desktop-dir "$$tmp_dir/Desktop" \
		--zipapp dist/$(APP).pyz; \
	"$$tmp_dir/prefix/bin/$(APP)" --version; \
	test -f "$$tmp_dir/Desktop/Telachat.desktop"; \
	grep -F "Exec=$$tmp_dir/prefix/bin/" "$$tmp_dir/Desktop/Telachat.desktop" >/dev/null

linux-rpm:
	packaging/linux/build-rpm.sh

install:
	mkdir -p "$(PREFIX)/bin"
	install -m 0755 bin/$(APP) "$(PREFIX)/bin/$(APP)"
	install -m 0755 bin/$(APP)-gtk "$(PREFIX)/bin/$(APP)-gtk"
	install -m 0755 bin/$(APP)-tk "$(PREFIX)/bin/$(APP)-tk"
	install -m 0755 bin/$(APP)-gui "$(PREFIX)/bin/$(APP)-gui"
	mkdir -p "$(PREFIX)/share/man/man1"
	install -m 0644 docs/man/$(APP).1 "$(PREFIX)/share/man/man1/$(APP).1"
	install -m 0644 docs/man/$(APP)-gtk.1 "$(PREFIX)/share/man/man1/$(APP)-gtk.1"
	install -m 0644 docs/man/$(APP)-tk.1 "$(PREFIX)/share/man/man1/$(APP)-tk.1"

doctor:
	PYTHONPATH=src $(PYTHON) -m telachat doctor

clean:
	rm -rf build dist *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
