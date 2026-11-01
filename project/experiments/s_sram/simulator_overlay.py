"""Isolate the OpenRAM simulator launcher fix for explicit use_conda=False."""
import argparse,hashlib,json,os
from pathlib import Path
import shutil

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--receipt',type=Path,required=True);a=ap.parse_args()
    assert os.environ.get('SLURM_JOB_ID')
    src=a.source.resolve();dst=a.out.resolve();assert dst.is_relative_to(Path('/public/home/yuzelu/opt/eda')) and not dst.exists()
    rel=Path('compiler/characterizer/stimuli.py');old=(src/rel).read_text()
    needle='        cmd = "/bin/bash -c \'source {0}/bin/activate && {1} && conda deactivate\'".format(CONDA_HOME, cmd)'
    assert old.count(needle)==1
    new=old.replace(needle,'        if OPTS.use_conda:\n    '+needle)
    compile(new,str(rel),'exec')
    shutil.copytree(src,dst);(dst/rel).write_text(new)
    changed=[str(p.relative_to(src)) for p in src.rglob('*') if p.is_file() and '__pycache__' not in p.parts and sha(p)!=sha(dst/p.relative_to(src))]
    assert changed==[str(rel)]
    a.receipt.write_text(json.dumps(dict(source=str(src),destination=str(dst),changed=changed,original_sha256=sha(src/rel),patched_sha256=sha(dst/rel),scope='Only honor explicit use_conda=False when launching the actual configured SPICE executable; simulation and all measurements remain unchanged.'),indent=2)+'\n')
if __name__=='__main__':main()
