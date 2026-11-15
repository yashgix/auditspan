.PHONY: test lint data-check experiment

PYTHON ?= python3

test:
	$(PYTHON) -m unittest discover -s tests

lint:
	ruff check . && ruff format --check .

data-check:
	$(PYTHON) tools/fetch_data.py --verify

experiment:
	$(PYTHON) experiment.py --out results/metrics.json --v2-out results/metrics_v2.json
