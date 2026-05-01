import json
from pathlib import Path
data=json.loads(Path('fixtures/report.json').read_text())
assert data == {'region': 'sh', 'items': ['svc-a:tg-1001', 'svc-b:tg-1002'], 'count': 2}
print('OK')
