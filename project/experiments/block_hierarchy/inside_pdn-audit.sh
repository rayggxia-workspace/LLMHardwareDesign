#!/usr/bin/env bash
set -euo pipefail
trap 'rc=$?; trap - EXIT; set +e; bash collect_attempt_outputs.sh; hash_rc=$?; printf "%s\n" "$hash_rc" > output-hash-exit-code.txt; exit "$rc"' EXIT
source /OpenROAD-flow-scripts/env.sh
openroad -version > openroad-version.txt 2>&1
sha256sum "$(command -v openroad)" > tools.sha256
export LLHD_AUDIT_DB="$LLHD_BLOCK/flow/results/nangate45/llhd_vec_harness/base/6_final.odb"
test -f "$LLHD_AUDIT_DB"
sha256sum "$LLHD_AUDIT_DB" audit_pdn.tcl check_pdn_connectivity.tcl filter_pg_access.tcl > pdn-audit-inputs.sha256
# This audit reads the completed top and never writes back into its directory.
python3 - <<'PY'
import hashlib, json, os
from pathlib import Path
root = Path(os.environ['LLHD_BLOCK'])
records = []
for folder in ('reports', 'logs'):
    base = root / 'flow' / folder / 'nangate45/llhd_vec_harness/base'
    for path in sorted(base.glob('*via*')):
        if path.is_file():
            records.append({'path': str(path), 'bytes': path.stat().st_size,
                            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
Path('pdn-source-via-reports.json').write_text(json.dumps({
    'reports': records,
    'pdn_log': str(root / 'flow/logs/nangate45/llhd_vec_harness/base/2_4_floorplan_pdn.log'),
    'pdn_warnings': [line for line in (root / 'flow/logs/nangate45/llhd_vec_harness/base/2_4_floorplan_pdn.log').read_text().splitlines() if 'WARNING PDN-' in line],
    'note': 'Inventory only. An absent or empty failed-via report does not prove PG connectivity.'
}, indent=2) + '\n')
PY
openroad -exit audit_pdn.tcl 2>&1 | tee pdn-audit.log
