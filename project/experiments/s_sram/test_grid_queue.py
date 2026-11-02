"""Linux queue controls only; synthetic points do not qualify SRAM timing."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import types
from parallel_grid_overlay import HELPER


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    assert os.environ.get('SLURM_JOB_ID')
    out = a.out.resolve(); out.mkdir(exist_ok=False)
    options = types.SimpleNamespace(num_sim_threads=1)
    namespace = dict(OPTS=options)
    exec(HELPER, namespace)
    samples = namespace['_s_sram_grid_samples']
    os.environ['S_SRAM_GRID_WORKERS'] = '2'
    os.environ['S_SRAM_CHARACTERIZATION_AUDIT'] = str(out/'audit')

    class Fixture:
        def __init__(self, mode):
            self.mode = mode
        def set_load_slew(self, load, slew):
            self.load, self.slew = load, slew
        def run_delay_simulation(self):
            folder = Path(options.openram_temp)
            (folder/'started').write_text(str(time.monotonic()))
            time.sleep(1 if self.load == 0 else .1)
            if self.mode == 'raise' and self.load == 0:
                raise RuntimeError('Deliberate worker failure control')
            self.path_delays = dict(point=self.load)
            (folder/'finished').write_text(str(time.monotonic()))
            (folder/'observed-audit').write_text(os.environ['S_SRAM_CHARACTERIZATION_AUDIT'])
            return self.mode != 'false', {0: dict(point=self.load)}

    checks = {}
    for mode in ('positive', 'false', 'raise'):
        folder = out/mode; folder.mkdir()
        options.openram_temp = str(folder)+os.sep
        rejected = False
        try:
            results = samples(Fixture(mode), [(i, .16) for i in range(6)])
        except RuntimeError:
            rejected = True
        checks[mode] = rejected if mode == 'raise' else (
            not rejected and [row[1][0]['point'] for row in results] == list(range(6))
            and all(row[0] == (mode == 'positive') for row in results))
        if mode == 'positive':
            grid = folder/'independent-grid'
            checks['backfill_before_slowest_finishes'] = float((grid/'point-002/started').read_text()) < float((grid/'point-000/finished').read_text())
            observed = [(grid/('point-%03d' % i)/'observed-audit').read_text() for i in range(6)]
            checks['isolated_audit_directories'] = len(set(observed)) == 6
    try:
        os.waitpid(-1, os.WNOHANG)
        checks['all_own_children_reaped'] = False
    except ChildProcessError:
        checks['all_own_children_reaped'] = True
    receipt = dict(passed=all(checks.values()), qualified=False, checks=checks,
                   scope='Synthetic process queue controls only; not SRAM simulation or timing qualification',
                   helper_sha256=hashlib.sha256(Path(__file__).with_name('parallel_grid_overlay.py').read_bytes()).hexdigest())
    (out/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt)); assert receipt['passed']


if __name__ == '__main__':
    main()
