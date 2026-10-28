"""Actual guard simulation plus a disabled-checker negative control."""
import json
import sys
from pathlib import Path


def control(root, out, cpus, run):
    from io_slots import file_sha
    from revision300_rtl import COMPILER
    assert cpus == 16
    rtl = root/'project/rtl/block_library_v1/block_v1_m.sv'
    bench = root/'project/experiments/block_v1/test_matrix_overflow_guard.cpp'
    original = rtl.read_text()
    pattern = 'wire observed_acc_overflow=|((~(acc_sign_left^acc_sign_right))&(acc_sign_result^acc_sign_left));'
    assert original.count(pattern) == 1
    bad = out/'negative/block_v1_m.sv';bad.parent.mkdir()
    bad.write_text(original.replace(pattern, "wire observed_acc_overflow=1'b0;"))
    for label, source in [('positive', rtl), ('negative', bad)]:
        run([COMPILER, '--cc', '--exe', '--build', '-j', '16', '-Wno-fatal',
             '--public-flat-rw', '--x-initial', 'unique', '--x-assign', 'unique',
             '--top-module', 'block_v1_m', '-Mdir', str(out/('obj-'+label)),
             '-CFLAGS', '-std=c++17 -O2', source, bench], label+'-build.log')
    reports = []
    for name, initial, seed in [('ones',1,121), ('random121',2,121), ('random122',2,122)]:
        run([out/'obj-positive/Vblock_v1_m', '+verilator+rand+reset+'+str(initial),
             '+verilator+seed+'+str(seed)], name+'.json')
        report = json.loads((out/(name+'.json')).read_text())
        assert report['passed'] is True and report['fault_injections'] == 4
        reports.append(report)
    assert reports[0] == reports[1] == reports[2]
    harness = out/'expect_failure.py'
    harness.write_text("""import json,subprocess,sys
r=subprocess.run([sys.argv[1]],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
assert r.returncode!=0 and 'expected signed overflow rejection' in r.stderr,(r.returncode,r.stdout,r.stderr)
print(json.dumps(dict(passed=True,negative_rejected=True,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)))
""")
    run([sys.executable, harness, out/'obj-negative/Vblock_v1_m'], 'negative-control.json')
    negative = json.loads((out/'negative-control.json').read_text())
    assert negative['negative_rejected'] is True
    result = dict(passed=True, rtl_sha256=file_sha(rtl), bench_sha256=file_sha(bench),
                  disabled_checker_rtl_sha256=file_sha(bad), positive_initial_runs=3,
                  positive=reports[0], negative=negative, qualified_hard_macro=False,
                  scope='S64 overflow fault-injection guard only, outside legal input magnitude; legacy and packed paths, both signs, rejection/held response/old completed result preserved. Negative physically disables checker in a separate simulation source.')
    (out/'revision300-m-guard-control.json').write_text(json.dumps(result, indent=2)+'\n')

