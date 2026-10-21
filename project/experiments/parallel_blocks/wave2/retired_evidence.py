"""Seal existing failed audit bytes in a new attempt, retaining every failure."""
import hashlib
import json
from pathlib import Path

parent = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7')
Path('retired').mkdir()
records = {}
for attempt in ('parallel-blocks-wave2-01', 'parallel-blocks-wave2-04'):
    original = parent / attempt / 'completion.json'
    raw = original.read_bytes()
    item = json.loads(raw)
    assert item['artifact_audit_failures'] > 0
    destination = Path('retired') / (attempt + '-completion.json')
    destination.write_bytes(raw)
    assert original.read_bytes() == destination.read_bytes()
    records[attempt] = dict(original=str(original), copied_to=str(destination), sha256=hashlib.sha256(raw).hexdigest(),
        original_artifact_audit_failures=item['artifact_audit_failures'],
        tasks={name:dict(exit_code=row['exit_code'], checksum_audits=row['checksum_audits'],
            observed_tool_gates_pass=row.get('observed_tool_gates_pass'),
            declared_validation_pass=row.get('declared_validation_pass')) for name,row in item['tasks'].items()})
Path('validation.json').write_text(json.dumps(dict(passed=True, kind='Failed audit byte preservation only',
    retired_audits=records, physical_results_accepted=False,
    scope='Cancelled tasks lack output manifests; original audits remain FAILED. This only seals their already-written records in a fresh directory.'),indent=2)+'\n')
