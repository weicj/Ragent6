import json
from pathlib import Path

expected = {
    "incident": "inc-481",
    "primary_root": "tenantless-cache-key",
    "selected_action": "quarantine-and-replay",
    "reject": ["restart-api", "raise-timeout"],
    "guards": {"dry_run": True, "tenant_scope": True},
    "verify": ["tenant-isolation", "replay-window"],
}
actual = json.loads(Path("fixtures/remediation.json").read_text())
assert actual == expected
print("OK")
