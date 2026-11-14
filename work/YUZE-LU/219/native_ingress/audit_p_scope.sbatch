#!/usr/bin/env bash
set -euo pipefail
cd "$1"
g="$2"
root=/public/home/yuzelu/project-circuit
package="$g/../request-runtime-r2"
source="$g/main-source"
stock="$root/issue250-pair27-full-programmed-20261112-01/source-tracked/project/rtl/block_local_native"
tool="$root/issue250-u-n32-stored-link-20261112-01/tool.sh"
vlt=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
out="$PWD/results-$SLURM_JOB_ID"
mkdir -p "$out" tmp
(cd "$source" && sha256sum --check --quiet source.sha256)
sha256sum "$stock/record_range_iterator.sv" p_scope_admission_probe.sv p_scope_admission_probe.cpp > "$out/source.sha256"
bash "$tool" "$vlt" --cc --exe --build -j "$SLURM_CPUS_PER_TASK" --top-module p_scope_admission_probe \
  --Mdir "$out/obj" -Wno-fatal p_scope_admission_probe.sv "$PWD/p_scope_admission_probe.cpp" \
  "$source/p_scope128_decode.sv" "$source/p_scope_range_service.sv" "$stock/record_range_iterator.sv" > "$out/build.log" 2>&1
/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python - "$package" "$g/native-dispatch-109637/report.json" "$out" "$tool" <<'PY'
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from hashlib import file_digest
import json, os, subprocess, sys
from pathlib import Path

package,audit,out,tool = map(Path, sys.argv[1:])
def checksum(path):
    with path.open('rb') as f:
        return file_digest(f, 'sha256').hexdigest()
seal = package/'proof.sha256'
hashes = dict(tuple(reversed(row.split('  ',1))) for row in seal.read_text().splitlines())
direct = json.loads(audit.read_bytes())
assert checksum(seal) == direct['package_proof_sha256']
for name in ('witness.json','mother-descriptors.tsv'):
    assert checksum(package/name) == hashes[name]
witness = json.loads((package/'witness.json').read_bytes())
topology = witness['topology']
assert topology == 25001
def run(phase):
    step = phase['step']
    name = f'phase-{step}/descriptors.bin'
    assert checksum(package/name) == hashes[name]
    return step, subprocess.check_output(["bash", str(tool), str(out/'obj/Vp_scope_admission_probe'),
                                           str(package/name), str(topology), '0'], text=True)
totals = Counter()
examples = {}
phases = witness['phases']
with (out/'by-phase.tsv').open('w') as out_table:
    out_table.write('step\topcode\tvocabulary_marker\tfull_k\tstatus\tcalls\tfirst_byte_offset\n')
    with ThreadPoolExecutor(max_workers=int(os.environ['SLURM_CPUS_PER_TASK'])) as pool:
        for step, rows in pool.map(run, phases):
            for row in rows.strip().splitlines():
                if row.startswith("OPENROAD: "):
                    continue
                op, vocab, full_k, status, calls, offset = map(int, row.split())
                key = (op,vocab,full_k,status)
                totals[key] += calls
                examples.setdefault(key,(step,offset))
                out_table.write(f'{step}\t{row}\n')
assert sum(totals.values()) == direct['counts']['header_matches_unqualified']
records = [dict(opcode=op,vocabulary_marker=bool(vocab),full_k=full_k,status=status,calls=count,
                example_step=examples[key][0],example_byte_offset=examples[key][1])
           for key,count in sorted(totals.items()) for op,vocab,full_k,status in (key,)]
by_status = Counter()
for row in records:
    by_status[row['status']] += row['calls']
report = dict(schema='block-v2-p-provider-admission/1', status='descriptor_guard_only',
              package_sha256=checksum(seal), direct_audit_sha256=checksum(audit),
              placed_topology=topology, source_inventory_sha256=checksum(out/'source.sha256'),
              by_phase_sha256=checksum(out/'by-phase.tsv'),
              p_scope_calls=sum(totals.values()), by_status=by_status, records=records,
              conditional_inputs=['CRC was verified by the sealed native CALL audit',
                                  'job and epoch match the descriptor input key'],
              unverified=['live input copy and window ownership','P result publication','end-to-end request retirement'])
(out/'report.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps(by_status,sort_keys=True))
PY
sha256sum "$out/"{by-phase.tsv,report.json}
