#!/usr/bin/env sh
cd "$(dirname "$0")"
python3 - <<'PY'
from normalizer import normalize_id
assert normalize_id('00042') == '42'
assert normalize_id('000') == '0'
assert normalize_id('4200') == '4200'
print('PASS')
PY
