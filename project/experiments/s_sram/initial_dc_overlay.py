"""Prepare an isolated ngspice initial-DC and input-audit tool overlay.

Keeps native Gear, tolerances, time step, measurements and acceptance functions.
Only ngspice UIC is removed. No running installation or simulation is modified.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


AUDIT = r'''
def _s_sram_audit_begin(stimulus):
    import os, re, hashlib, json, time
    from pathlib import Path
    root = os.environ.get("S_SRAM_CHARACTERIZATION_AUDIT")
    if not root:
        return None
    root = Path(root); root.mkdir(exist_ok=True, parents=True)
    objects = root / "objects"; objects.mkdir(exist_ok=True)
    runs = root / "runs"; runs.mkdir(exist_ok=True)
    run = runs / ("%06d" % len(list(runs.iterdir())))
    run.mkdir(exist_ok=False)
    inputs = {}
    def capture(path):
        path = Path(path).resolve()
        if str(path) in inputs:
            return
        data = path.read_bytes(); digest = hashlib.sha256(data).hexdigest()
        target = objects / digest
        if not target.exists():
            target.write_bytes(data)
        assert hashlib.sha256(target.read_bytes()).hexdigest() == digest
        inputs[str(path)] = digest
        for line in data.decode().splitlines():
            match = re.match(r'^\s*\.include\s+(?:"([^"]+)"|(\S+))', line, re.I)
            if match:
                include = Path(match.group(1) or match.group(2))
                capture(include if include.is_absolute() else path.parent / include)
    capture(stimulus)
    init = Path(OPTS.openram_temp) / '.spiceinit'
    if init.is_file():
        capture(init)
    record = dict(qualified=False, status='running', stimulus=str(stimulus),
                  inputs=inputs, started_unix=time.time())
    (run / 'receipt.json').write_text(json.dumps(record, indent=2)+'\n')
    return root, run, record

def _s_sram_audit_end(state, returncode):
    if state is None:
        return
    import hashlib, json, time
    from pathlib import Path
    root, run, record = state
    for path, digest in record['inputs'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
    outputs = {}
    for name in ('timing.lis', 'spice_stdout.log', 'spice_stderr.log'):
        path = Path(OPTS.openram_temp) / name
        if not path.is_file():
            continue
        data = path.read_bytes(); digest = hashlib.sha256(data).hexdigest()
        target = root / 'objects' / digest
        if not target.exists():
            target.write_bytes(data)
        assert hashlib.sha256(target.read_bytes()).hexdigest() == digest
        outputs[str(path)] = digest
    record.update(status='simulator_returned_not_native_acceptance',
                  returncode=returncode, outputs=outputs,
                  seconds=time.time()-record['started_unix'])
    (run / 'receipt.json').write_text(json.dumps(record, indent=2)+'\n')

'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--destination', type=Path, required=True)
    ap.add_argument('--receipt', type=Path, required=True)
    a = ap.parse_args()
    assert not a.destination.exists() and not a.receipt.exists()
    relative = Path('compiler/characterizer/stimuli.py')
    assert not (a.source/relative).is_symlink()
    original = (a.source/relative).read_text()
    old = 'self.sf.write(".TRAN {0}p {1}n 0n {0}p UIC\\n".format(timestep, end_time))'
    new = old.replace('p UIC', 'p')
    assert original.count(old) == 2  # ngspice and hspice branches
    changed = original.replace(old, new, 1)
    anchor = '        proc = subprocess.run(cmd, stdout=spice_stdout, stderr=spice_stderr, shell=True, cwd=OPTS.openram_temp)'
    assert changed.count(anchor) == 1
    changed = changed.replace(anchor, '        audit_state = _s_sram_audit_begin(temp_stim)\n'+anchor+'\n        _s_sram_audit_end(audit_state, proc.returncode)')
    changed += '\n'+AUDIT
    compile(changed, str(relative), 'exec')
    shutil.copytree(a.source, a.destination, symlinks=True)
    assert not (a.destination/relative).is_symlink()
    (a.destination/relative).write_text(changed)
    assert (a.source/relative).read_text() == original
    sha = lambda data: hashlib.sha256(data).hexdigest()
    a.receipt.write_text(json.dumps(dict(
        source=str(a.source.resolve()), destination=str(a.destination.resolve()),
        changed=[relative.as_posix()], original_sha256=sha(original.encode()),
        patched_sha256=sha((a.destination/relative).read_bytes()),
        helper_sha256=sha(Path(__file__).read_bytes()),
        scope='ngspice initial DC instead of UIC; content-addressed input/output capture around each simulator call. Native Gear, RELTOL, timestep, load/slew grid, measurements and all native acceptance functions retained. Simulation completion alone is not acceptance.'
    ), indent=2)+'\n')


if __name__ == '__main__':
    main()
