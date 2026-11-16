"""Run four SRAM states and actual wrong-row fault on inactive-word probe."""
import argparse,json,subprocess,sys
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();r=a.directory.resolve()
    wsldir='/mnt/'+r.drive[0].lower()+r.as_posix()[2:]
    script='''import json,subprocess
from pathlib import Path
r=Path(ROOT)
iv='/tmp/yzl-issue219-iverilog12-20261109/install/bin/iverilog'
vv='/tmp/yzl-issue219-iverilog12-20261109/install/bin/vvp'
def run(args,name,negative=None):
    with (r/name).open('xb') as f:p=subprocess.run(args,cwd=r,stdout=f,stderr=subprocess.STDOUT)
    if negative:
        if p.returncode==0 or negative.encode() not in (r/name).read_bytes():raise RuntimeError('fault was not detected '+name)
    elif p.returncode:raise RuntimeError('inactive-word probe failed '+name)
    return {'returncode':p.returncode,'bytes':(r/name).stat().st_size}
result={'build':run([iv,'-g2012','-Irtl/block_v2','-s','tb_resident_row_probe','-o','probe.vvp','-f','compile.f'],'build.log')}
for i in range(4):result[str(i)]=run([vv,'probe.vvp','+sinit='+str(i)],'simulate-'+str(i)+'.log')
original=(r/'tb_resident_row_probe.sv').read_text();wrong=original.replace('command(5,rr<<3,','command(5,0,')
if original==wrong:raise RuntimeError('row-index fault not injected')
(r/'tb_negative_row.sv').write_text(wrong);files=(r/'compile.f').read_text().splitlines()
result['negative_build']=run([iv,'-g2012','-Irtl/block_v2','-s','tb_resident_row_probe','-o','negative.vvp','tb_negative_row.sv',*files[1:]],'negative-build.log')
result['negative']=run([vv,'negative.vvp','+sinit=3'],'negative.log','row result differs')
(r/'run-result.json').write_text(json.dumps(result,indent=2)+'\\n');print(json.dumps(result))
'''.replace('ROOT',repr(wsldir))
    with (r/'wsl-run.log').open('xb') as f:child=subprocess.run(['wsl.exe','--exec',
        '/tmp/yzl-issue219-python3128-20261109/install/bin/python3.12','-B','-c',script],stdout=f,stderr=subprocess.STDOUT)
    if child.returncode:print(repr((r/'wsl-run.log').read_bytes()[-3000:]));raise SystemExit(child.returncode)
    sys.path.insert(0,str(Path('project/experiments/block_synthesis').resolve()))
    from resident_mask_probe import qualification
    q=qualification(r,[r/f'simulate-{i}.log' for i in range(4)])
    (r/'qualification.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q['proof']))


if __name__=='__main__':main()
