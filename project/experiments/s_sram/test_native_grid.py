"""Real OpenRAM/fork integration control, not a Liberty or whole-S qualification.

Use an existing physical producer's immutable full AND trimmed circuit. The
temporary netlist-only object supplies graph/measurement metadata only. Checks
reject any regenerated simulation circuit being used in place of the real one.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--actual-circuit', type=Path, required=True)
    ap.add_argument('--actual-trimmed', type=Path, required=True)
    ap.add_argument('--actual-sha256', required=True)
    ap.add_argument('--trimmed-sha256', required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    assert os.environ.get('SLURM_JOB_ID')
    assert sha(a.actual_circuit) == a.actual_sha256
    assert sha(a.actual_trimmed) == a.trimmed_sha256
    out = a.out.resolve(); out.mkdir(exist_ok=False)
    receipt = dict(passed=False, qualified=False,
        scope='Actual-circuit/native OpenRAM independent-grid integration only; no full characterization, leakage power, geometry or whole S acceptance')
    def save():
        (out/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    try:
        config = out/'config.py'
        config.write_text(Path(__file__).with_name('openram_config.py').read_text()+'\n'
            'words_per_row=2\ndelay_chain_stages=25\nnetlist_only=True\ncheck_lvsdrc=False\n'
            'num_sim_threads=1\nuse_specified_corners=[("TT",1.1,25)]\n'
            'output_path='+repr(str(out)+os.sep)+'\n')
        import openram
        openram.OPTS.top_process = 'openram'
        openram.init_openram(str(config)); openram.setup_bitcell()
        from openram import sram
        from openram.characterizer import delay
        memory = sram()
        circuit = out/'actual.sp'; circuit.write_bytes(a.actual_circuit.read_bytes())
        d = delay(memory.s, str(circuit), ('TT', 1.1, 25))
        d.analysis_init('1'*memory.s.addr_size, memory.s.word_size-1)
        Path(d.trim_sp_file).write_bytes(a.actual_trimmed.read_bytes())
        assert sha(d.trim_sp_file) == a.trimmed_sha256
        d.period = 10/3
        points = [(0.2091, .005), (1.6728, .04), (6.6912, .16)]
        start = time.monotonic()
        data = d.simulate_loads_and_slews(points, 0)
        checks = {}
        rows = []
        for i, point in enumerate(points):
            folder = Path(openram.OPTS.openram_temp)/'independent-grid'/('point-%03d' % i)
            text = (folder/'timing.lis').read_text()
            values = {m.group(1):float(m.group(2)) for m in re.finditer(
                r'(?mi)^([a-z0-9_]+)\s*=\s*([-+\d.e]+)', text)}
            bits = {}
            for key, value in values.items():
                if key.startswith(('v_q_', 'v_qbar_')) and any(t in key for t in ('read_zero','read_one','write_zero','write_one')):
                    high = ('_one' in key) != key.startswith('v_qbar_')
                    bits[key] = value > .99 if high else 0 <= value < .11
            assert len(bits) == 8
            bits.update(output_one=values.get('v_delay_lh0', -1) > .99,
                        output_zero=0 <= values.get('v_delay_hl0', 2) < .11,
                        sense_half=0 <= values.get('delay_sen0', -1) <= (10/6)*1e-9)
            checks[str(i)] = all(bits.values())
            rows.append(dict(point=point, checks=bits, measurements=values,
                             log_sha256=sha(folder/'timing.lis')))
        assert sha(a.actual_circuit) == a.actual_sha256 == sha(circuit)
        assert sha(a.actual_trimmed) == a.trimmed_sha256 == sha(d.trim_sp_file)
        assert all(len(values) == len(points) for port in data for values in port.values())
        receipt.update(checks=checks, points=rows, native_table_data=data,
            seconds=time.monotonic()-start, passed=all(checks.values()),
            actual_circuit_sha256=a.actual_sha256, actual_trimmed_sha256=a.trimmed_sha256)
        save(); assert receipt['passed']
        openram.end_openram()
    except BaseException as e:
        receipt['failure'] = repr(e)
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
