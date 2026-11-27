# MapSlop P0 — Linux/macOS/WSL or devcontainer. Run make setup once.
PYTHON ?= python3
HOST ?= 127.0.0.1
PORT ?= 8080
OUT ?= pedome
CACHE := .cache/mapslop
VENV := .venv
PY := $(VENV)/bin/python

.PHONY: setup build test serve
setup:
	$(PYTHON) -m venv "$(VENV)"
	$(PY) -m pip install -r requirements.txt
	npm ci --ignore-scripts --no-audit --no-fund
	$(PY) tools/setup-upstream.py "$(CACHE)"

build:
	@test -x "$(PY)" && test -f "$(CACHE)/three-vendor/LICENSE" || { echo "Run make setup first"; exit 1; }
	$(PY) tools/prepare-pedome.py "$(CACHE)/nairobi" "$(OUT)" --osm-json data/pedome/pedome-osm.json --flat --three-vendor "$(CACHE)/three-vendor"

test:
	@test -f "$(OUT)/build-report.json" || { echo "Run make build first"; exit 1; }
	npm --prefix "$(OUT)" test
	$(PY) -c 'import json,sys; d=json.load(open(sys.argv[1])); assert not d["fixture"] and d["roads"]>0 and d["buildings"]>0, d; print(d)' "$(OUT)/build-report.json"

serve:
	@test -f "$(OUT)/index.html" || { echo "Run make build first"; exit 1; }
	exec $(PY) -m http.server "$(PORT)" --bind "$(HOST)" --directory "$(OUT)"
