"""Isolate independent native load/slew simulations in a bounded fork queue.

The minimum-period search and leakage measurements remain native and serial.
Every grid worker calls the original run_delay_simulation and all its checks.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


HELPER = r'''
def _s_sram_grid_samples(characterizer, load_slews):
    import os, pickle, traceback
    from pathlib import Path
    workers = int(os.environ.get('S_SRAM_GRID_WORKERS', '1'))
    if workers <= 1:
        return None
    allocated = int(os.environ['SLURM_CPUS_PER_TASK'])
    assert 1 <= workers < allocated
    assert OPTS.num_sim_threads == 1
    root = Path(OPTS.openram_temp) / 'independent-grid'
    root.mkdir(exist_ok=False)
    todo = list(enumerate(load_slews)); active = {}; results = {}
    parent_audit = os.environ.get('S_SRAM_CHARACTERIZATION_AUDIT')
    while todo or active:
        while todo and len(active) < workers:
            index, (load, slew) = todo.pop(0)
            folder = root / ('point-%03d' % index); folder.mkdir()
            pid = os.fork()
            if pid == 0:
                try:
                    stream = (folder/'worker.log').open('w')
                    os.dup2(stream.fileno(), 1); os.dup2(stream.fileno(), 2)
                    OPTS.openram_temp = str(folder)+os.sep
                    characterizer.output_path = OPTS.openram_temp
                    if parent_audit:
                        os.environ['S_SRAM_CHARACTERIZATION_AUDIT'] = str(Path(parent_audit)/('grid-%03d' % index))
                    characterizer.set_load_slew(load, slew)
                    success, values = characterizer.run_delay_simulation()
                    value = (success, values, getattr(characterizer, 'path_delays', None))
                    (folder/'result.pkl').write_bytes(pickle.dumps(value, protocol=4))
                    stream.flush()
                    os._exit(0)
                except BaseException:
                    traceback.print_exc()
                    try:
                        stream.flush()
                    finally:
                        os._exit(1)
            active[pid] = (index, folder)
        # Wait for any completed independent point, then immediately backfill.
        # Only these child PIDs are owned by this queue; do not reap unrelated children.
        import time
        finished = []
        for pid in list(active):
            got, status = os.waitpid(pid, os.WNOHANG)
            if got:
                finished.append((pid, status))
        if not finished:
            time.sleep(0.1)
            continue
        for pid, status in finished:
            index, folder = active.pop(pid)
            if not os.WIFEXITED(status) or os.WEXITSTATUS(status) != 0:
                # Reap remaining own workers before reporting the failure.
                for other in active:
                    os.waitpid(other, 0)
                raise RuntimeError('Native grid worker failed: '+str(folder))
            results[index] = pickle.loads((folder/'result.pkl').read_bytes())
    assert len(results) == len(load_slews)
    return [results[index] for index in range(len(load_slews))]

'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--destination', type=Path, required=True)
    ap.add_argument('--receipt', type=Path, required=True)
    a = ap.parse_args()
    assert not a.destination.exists() and not a.receipt.exists()
    relative = Path('compiler/characterizer/delay.py')
    assert not (a.source/relative).is_symlink()
    original = (a.source/relative).read_text()
    offset = original.index('    def simulate_loads_and_slews(')
    head, body = original[:offset], original[offset:]
    loop = '        for load, slew in load_slews:'
    assert body.count(loop) == 1
    body = body.replace(loop, '        native_samples = _s_sram_grid_samples(self, load_slews)\n'
                        '        for sample_index, (load, slew) in enumerate(load_slews):')
    call = '            (success, delay_results) = self.run_delay_simulation()'
    assert body.count(call) == 1
    replacement = ('            if native_samples is None:\n'+call.replace('            ', '                ', 1)+'\n'
                   '            else:\n'
                   '                success, delay_results, paths = native_samples[sample_index]\n'
                   '                if paths is not None:\n'
                   '                    self.path_delays = paths')
    body = body.replace(call, replacement)
    changed = head+body+'\n'+HELPER
    compile(changed, str(relative), 'exec')
    shutil.copytree(a.source, a.destination, symlinks=True)
    assert not (a.destination/relative).is_symlink()
    (a.destination/relative).write_text(changed)
    assert (a.source/relative).read_text() == original
    sha = lambda data: hashlib.sha256(data).hexdigest()
    a.receipt.write_text(json.dumps(dict(source=str(a.source.resolve()),
        destination=str(a.destination.resolve()), changed=[relative.as_posix()],
        original_sha256=sha(original.encode()), patched_sha256=sha((a.destination/relative).read_bytes()),
        helper_sha256=sha(Path(__file__).read_bytes()),
        scope='Only independent grid scheduling changes: forked native run_delay_simulation, isolated temp/audit directories, ordered results and dynamic backfill. Original min-period search, leakage, measurements, native checks and table assembly retained.'
    ), indent=2)+'\n')


if __name__ == '__main__':
    main()
