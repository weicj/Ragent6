.PHONY: test mock audit clean

PYTHON ?= python3

test:
	$(PYTHON) -m compileall -q ragent6 scripts
	$(PYTHON) scripts/run_eval.py --manifest manifests/ragent6_0_2_0_en_US.json --adapter mock --out results/mock-0.2.0-en-US
	$(PYTHON) scripts/run_eval.py --manifest manifests/ragent6_0_2_0_zh_CN.json --adapter mock --out results/mock-0.2.0-zh-CN
	$(PYTHON) scripts/release_audit.py --manifest manifests/ragent6_0_2_0_en_US.json --suite-version 0.2.0 --locale en-US
	$(PYTHON) scripts/release_audit.py --manifest manifests/ragent6_0_2_0_zh_CN.json --suite-version 0.2.0 --locale zh-CN

mock:
	$(PYTHON) scripts/run_eval.py --manifest manifests/ragent6_0_2_0_en_US.json --adapter mock --out results/mock-0.2.0-en-US
	$(PYTHON) scripts/run_eval.py --manifest manifests/ragent6_0_2_0_zh_CN.json --adapter mock --out results/mock-0.2.0-zh-CN

audit:
	$(PYTHON) scripts/release_audit.py --manifest manifests/ragent6_0_2_0_en_US.json --suite-version 0.2.0 --locale en-US
	$(PYTHON) scripts/release_audit.py --manifest manifests/ragent6_0_2_0_zh_CN.json --suite-version 0.2.0 --locale zh-CN

clean:
	rm -rf results/mock-0.2.0-en-US results/mock-0.2.0-zh-CN
