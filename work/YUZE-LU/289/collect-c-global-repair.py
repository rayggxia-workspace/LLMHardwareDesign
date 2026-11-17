"""Collect completed global-RC experiments without qualifying a physical release."""
import hashlib
import json
import re
from pathlib import Path

root = Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117')
experiments = []
for directory in sorted((root / 'c-physical').glob('global-repair-v*')):
    status_file = directory / 'status.txt'
    if not status_file.exists():
        continue
    status = dict(line.split('=', 1) for line in status_file.read_text().splitlines())
    evidence = [status_file, directory / 'run.log']
    result = {'run': str(directory), 'exit_code': int(status['exit_code']), 'accepted': False}
    for stage in ('before', 'after'):
        counts_file = directory / (stage + '-counts.tsv')
        if not counts_file.exists():
            continue
        stage_result = {'counts': dict((key, int(value)) for key, value in
                                     (line.split() for line in counts_file.read_text().splitlines()))}
        evidence.append(counts_file)
        for name, delay in (('setup', 'max'), ('hold', 'min')):
            report = directory / (stage + '-' + name + '.rpt')
            stage_result[name + '_slack_ns'] = float(re.search(
                r'worst slack ' + delay + r'\s+([-+0-9.eE]+)', report.read_text())[1])
            evidence.append(report)
        result[stage] = stage_result
    for name in ('inputs-before.sha256', 'inputs-after.sha256', 'dot-guard.sha256',
                 'targeted-delay-budget.tsv', 'geometry-before.tsv', 'geometry-after.tsv'):
        report = directory / name
        if report.exists():
            evidence.append(report)
    result['evidence_sha256'] = {str(report): hashlib.sha256(report.read_bytes()).hexdigest()
                                 for report in evidence}
    experiments.append(result)

summary = {
    'accepted': False,
    'scope': 'Global-RC implementation experiments. Actual routed RC, full DRC, PG, '
             'function, state/control, geometry and model checks remain required.',
    'experiments': experiments,
}
output = root / 'c-physical/global-repair-summary.json'
output.write_text(json.dumps(summary, indent=2))
print(output)
