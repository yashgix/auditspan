.PHONY: test lint data-check experiment page

PYTHON ?= python3

test:
	$(PYTHON) -m unittest discover -s tests

lint:
	ruff check . && ruff format --check .

data-check:
	$(PYTHON) tools/fetch_data.py --verify

page:
	$(PYTHON) page.py

experiment:
	$(PYTHON) experiment.py --out results/metrics.json --v2-out results/metrics_v2.json --v2-1-out results/metrics_v2_1.json --heldout-out results/heldout.json
