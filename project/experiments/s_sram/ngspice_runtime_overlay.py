"""Isolate ngspice cwd/solver configuration; retain model checks and inputs."""
import argparse, hashlib, json, os, shutil
from pathlib import Path

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def patch(old):
    assert '        if OPTS.use_conda:\n' in old
    needle = '            ng_cfg.write("set ng_nomodcheck\\n")'
    assert old.count(needle) == 1
    new = old.replace(needle, '            ng_cfg.write("option klu\\n")')
    needle = 'proc = subprocess.run(cmd, stdout=spice_stdout, stderr=spice_stderr, shell=True)'
    assert new.count(needle) == 1
    new = new.replace(needle, 'proc = subprocess.run(cmd, stdout=spice_stdout, stderr=spice_stderr, shell=True, cwd=OPTS.openram_temp)')
    compile(new, 'stimuli.py', 'exec')
    assert 'ng_nomodcheck' not in new
    return new

def main():
    ap = argparse.ArgumentParser()
    for key in ('source','out','receipt'):
        ap.add_argument('--'+key,type=Path,required=True)
    a = ap.parse_args(); assert os.environ.get('SLURM_JOB_ID')
    src = a.source.resolve(); dst = a.out.resolve()
    assert dst.is_relative_to(Path('/public/home/yuzelu/opt/eda')) and not dst.exists()
    rel = Path('compiler/characterizer/stimuli.py')
    new = patch((src/rel).read_text())
    shutil.copytree(src,dst); (dst/rel).write_text(new)
    changed = [str(p.relative_to(src)) for p in src.rglob('*') if p.is_file() and '__pycache__' not in p.parts and sha(p)!=sha(dst/p.relative_to(src))]
    assert changed == [str(rel)]
    a.receipt.write_text(json.dumps(dict(source=str(src),destination=str(dst),changed=changed,original_sha256=sha(src/rel),patched_sha256=sha(dst/rel),scope='Launch ngspice in its existing temporary directory so local init applies; select KLU and configured threads; remove upstream ng_nomodcheck so BSIM model checks stay enabled. Circuit/stimulus/measurements/tolerances unchanged.'),indent=2)+'\n')

if __name__ == '__main__':
    main()
