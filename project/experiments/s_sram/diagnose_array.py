"""SPICE-only array/control diagnosis with ALL native delay checks retained.

No geometry, Liberty or physical qualification is produced. Execute independent
cases concurrently in an allocation; do not change a running physical producer.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import time


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--words-per-row', type=int, choices=(2, 4), required=True)
    ap.add_argument('--stages', type=int, choices=(9, 25, 31), required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--load-ff', type=float, default=6.6912)
    ap.add_argument('--slew-ns', type=float, default=0.16)
    ap.add_argument('--actual-circuit', type=Path)
    ap.add_argument('--actual-sha256')
    ap.add_argument('--actual-trimmed', type=Path)
    ap.add_argument('--actual-trimmed-sha256')
    ap.add_argument('--spice-threads', type=int, choices=(1, 8), default=8)
    a = ap.parse_args()
    assert os.environ.get('SLURM_JOB_ID')
    assert a.load_ff > 0 and a.slew_ns > 0
    out = a.out.resolve()
    out.mkdir(exist_ok=False, parents=True)
    r = dict(passed=False, qualified=False, words_per_row=a.words_per_row,
             stages=a.stages, period_ns=10/3, load_ff=a.load_ff, slew_ns=a.slew_ns,
             scope='Netlist-only diagnosis; no matching candidate geometry or library')

    def save():
        (out/'receipt.json').write_text(json.dumps(r, indent=2)+'\n')

    start = time.monotonic()
    try:
        original = Path(__file__).with_name('openram_config.py')
        cfg = out/'config.py'
        cfg.write_text(original.read_text() + '\n' +
                       f'words_per_row = {a.words_per_row}\ndelay_chain_stages = {a.stages}\n' +
                       f'output_path = {str(out)+os.sep!r}\n' +
                       'netlist_only = True\ncheck_lvsdrc = False\n' +
                       f'num_sim_threads = {a.spice_threads}\nuse_specified_corners = [("TT",1.1,25)]\n')
        r['config_sha256'] = sha(cfg)
        r['physical_checks_disabled_only_for_explicit_netlist_diagnosis'] = True
        save()
        import openram
        openram.OPTS.top_process = 'openram'
        openram.init_openram(str(cfg))
        openram.setup_bitcell()
        from openram import sram
        from openram.characterizer import delay
        memory = sram()
        circuit = out/'sram.sp'
        memory.sp_write(str(circuit))
        if a.actual_circuit:
            assert a.actual_sha256 and sha(a.actual_circuit) == a.actual_sha256
            circuit.write_bytes(a.actual_circuit.read_bytes())
            assert sha(circuit) == a.actual_sha256
            r.update(actual_circuit=str(a.actual_circuit.resolve()),
                     actual_circuit_sha256=a.actual_sha256,
                     scope='Actual generated transistor netlist at target period, all native checks retained; no Liberty or complete S qualification')
        # Native run_delay_simulation passes a basename to the simulator. Its
        # runtime cwd is OPENRAM_TMP, so stimuli must use that native directory.
        d = delay(memory.s, str(circuit), ('TT', 1.1, 25))
        d.analysis_init('1'*memory.s.addr_size, memory.s.word_size-1)
        # analysis_init regenerates trimmed.sp from the in-memory SRAM object.
        # A netlist-only object can have different transistor sizing from the
        # physical producer. Bind BOTH simulation inputs after this regeneration.
        if a.actual_circuit:
            assert a.actual_trimmed and a.actual_trimmed_sha256
            assert sha(a.actual_trimmed) == a.actual_trimmed_sha256
            trimmed = Path(d.trim_sp_file)
            trimmed.write_bytes(a.actual_trimmed.read_bytes())
            assert sha(trimmed) == a.actual_trimmed_sha256
            r.update(actual_trimmed=str(a.actual_trimmed.resolve()),
                     actual_trimmed_sha256=a.actual_trimmed_sha256)
            save()
        d.set_load_slew(a.load_ff, a.slew_ns)
        d.period = 10/3
        d.targ_read_ports = list(memory.s.read_ports)
        d.targ_write_ports = [memory.s.write_ports[0]]
        native_success, native_values = d.run_delay_simulation()
        if a.actual_circuit:
            assert sha(circuit) == a.actual_sha256
            assert sha(Path(d.trim_sp_file)) == a.actual_trimmed_sha256
        logpath = Path(openram.OPTS.openram_temp)/'timing.lis'
        text = logpath.read_text()
        values = {m.group(1): float(m.group(2)) for m in re.finditer(
            r'(?mi)^([a-z0-9_]+)\s*=\s*([-+\d.e]+)', text)}
        checks = {}
        for key, value in values.items():
            if key.startswith(('v_q_', 'v_qbar_')) and any(
                    x in key for x in ('read_zero', 'read_one', 'write_zero', 'write_one')):
                high = ('_one' in key) != key.startswith('v_qbar_')
                checks[key] = value > 0.99 if high else 0 <= value < 0.11
        assert len(checks) == 8, checks
        checks['output_read_one'] = values.get('v_delay_lh0', -1) > 0.99
        checks['output_read_zero'] = 0 <= values.get('v_delay_hl0', 2) < 0.11
        sense_ns = values.get('delay_sen0', -1)*1e9
        checks['sense_enable_within_half_period'] = 0 <= sense_ns <= d.period/2
        checks['all_native_measurement_checks'] = bool(native_success)
        r.update(checks=checks, native_values=native_values, measurements=values,
                 independent_sense_delay_ns=sense_ns,
                 simulation_log=str(logpath), simulation_log_sha256=sha(logpath),
                 circuit_sha256=sha(circuit),
                 final_input_files={str(p): sha(p) for p in
                                    [circuit, *[Path(openram.OPTS.openram_temp)/n for n in
                                                ('delay_stim.sp','delay_meas.sp','trimmed.sp')]]})
        r['passed'] = all(checks.values())
        save()
        openram.end_openram()
    except BaseException as e:
        r['failure'] = repr(e)
        raise
    finally:
        paths=[out/n for n in ('config.py','sram.sp','delay_stim.sp','delay_meas.sp')]
        if 'openram' in locals():
            paths += [Path(openram.OPTS.openram_temp)/n for n in
                      ('timing.lis','trimmed.sp','delay_stim.sp','delay_meas.sp')]
        r['retained_files']={str(p):sha(p) for p in paths if p.is_file()}
        r['seconds'] = time.monotonic()-start
        save()


if __name__ == '__main__':
    main()
