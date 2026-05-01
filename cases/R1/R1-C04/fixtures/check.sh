#!/usr/bin/env sh
python3 - <<'PY'
import json
data = json.load(open('fixtures/out/report.json', encoding='utf-8'))
assert data == {'currency': 'USD', 'total_due': 42, 'vip_count': 2, 'ship_mode': 'ground'}
print('PASS')
PY
