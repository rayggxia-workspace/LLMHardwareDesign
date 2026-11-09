"""Run an actual wrong-K command on a separately compiled complete probe."""
import argparse,json,subprocess
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();root=a.directory.resolve()
    wsl='/mnt/'+root.drive[0].lower()+root.as_posix()[2:]
    code='''import json,subprocess
from pathlib import Path
r=Path(ROOT)
assert (r/'probe.vvp').is_file()
with (r/'negative-k.log').open('xb') as f:
 p=subprocess.run(['/tmp/yzl-issue219-iverilog12-20261109/install/bin/vvp','probe.vvp','+sinit=3','+badk'],cwd=r,stdout=f,stderr=subprocess.STDOUT)
log=(r/'negative-k.log').read_bytes()
result={'returncode':p.returncode,'bytes':len(log),'actual_K_fault':b'BATCH_K_FAULT' in log,'numeric_failure':b'resident M result mismatch' in log}
(r/'negative-k-result.json').write_text(json.dumps(result,indent=2)+'\\n')
if p.returncode==0 or not result['actual_K_fault'] or not result['numeric_failure']:raise RuntimeError('wrong-K injection was not numerically detected')
print(json.dumps(result))
'''.replace('ROOT',repr(wsl))
    with (root/'negative-k-wsl.log').open('xb') as f:
        proc=subprocess.run(['wsl.exe','--exec','/tmp/yzl-issue219-python3128-20261109/install/bin/python3.12','-B','-c',code],stdout=f,stderr=subprocess.STDOUT)
    if proc.returncode:raise SystemExit(proc.returncode)
    print((root/'negative-k-result.json').read_text())


if __name__=='__main__':main()
