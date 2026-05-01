.PHONY: test mock audit clean

PYTHON ?= python3

test:
	$(PYTHON) -m compileall -q ragent6 scripts
	$(PYTHON) scripts/run_eval.py --manifest manifests/ragent6.json --adapter mock --out results/mock-1.1.0
	$(PYTHON) scripts/release_audit.py --manifest manifests/ragent6.json --suite-version 1.1.0

mock:
	$(PYTHON) scripts/run_eval.py --manifest manifests/ragent6.json --adapter mock --out results/mock-1.1.0

audit:
	$(PYTHON) scripts/release_audit.py --manifest manifests/ragent6.json --suite-version 1.1.0

clean:
	rm -rf results/mock-1.1.0
