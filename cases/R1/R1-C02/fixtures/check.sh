#!/bin/sh
python3 - <<'PY'
import json
data=json.load(open('fixtures/decision.json'))
assert data.get('winner') == 'delta'
assert 'offline' in data.get('reason','').lower()
assert 'risk' in data.get('reason','').lower()
PY
