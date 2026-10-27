"""Two complete actual-final mixed regressions inside one bounded allocation."""
import concurrent.futures
import json
import os
import subprocess
import sys
import time
from native_allocation_group import file_sha, memory_snapshot


def verify(root, out, cpus):
    assert cpus == 48
    memory = memory_snapshot()
    # Scheduling estimate, not a measured peak of these new final models.
    simultaneous = 2 if memory['MemAvailable'] >= 2*128*1024**3*1.2 else 1
    def execute(policy):
        mode = 'native-composed-'+policy
        folder = out.parent/mode; folder.mkdir(exist_ok=False)
        env = dict(os.environ, OMP_NUM_THREADS='24', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
        started = time.time()
        with (folder/'group-child.log').open('w') as stream:
            code = subprocess.run([sys.executable, str(root/'project/experiments/block_v1/worker.py'), str(root), mode, '24'],
                                  cwd=folder, env=env, stdout=stream, stderr=subprocess.STDOUT).returncode
        record = dict(mode=mode, cpus=24, returncode=code, started=started, finished=time.time(), passed=False)
        receipt = folder/'receipt.json'; proof = folder/'native-composed-function.json'
        try:
            bound = json.loads(receipt.read_text()); result = json.loads(proof.read_text())
            record.update(receipt_sha256=file_sha(receipt), proof_sha256=file_sha(proof))
            record['passed'] = bool(code == 0 and bound['passed'] is True and bound['cpus'] == 24 and bound['mode'] == mode
                                    and bound['outputs'][proof.name] == file_sha(proof) and result['passed'] is True
                                    and result['policy'] == policy.upper() and len(result['cases']) == 6)
        except (OSError, KeyError, ValueError) as error: record['validation_error'] = repr(error)
        return record
    with concurrent.futures.ThreadPoolExecutor(max_workers=simultaneous) as pool:
        children = list(pool.map(execute, ['a', 'c']))
    result = dict(schema='block-v1-native-composed-group/1', passed=all(c['passed'] for c in children), children=children,
                  allocated_cpus=cpus, simultaneous_workers=simultaneous, maximum_concurrent_child_cpu_ceilings=24*simultaneous,
                  memory_preflight=memory, per_child_memory_estimate_bytes=128*1024**3, memory_safety_factor=1.2,
                  qualified_hard_macro=False, scope='A/C real final C8/S16K/T6K with mapped glue, six full mixed initial/stall cases each. Parent physical, recovery/epoch, boundary and twelve-layer gates remain separate.')
    (out/'native-composed-group.json').write_text(json.dumps(result, indent=2)+'\n')
    assert result['passed'], 'A composed child failed; completed peer evidence is retained'
