"""Execute complete finite-S row programs and an actual wrong-row fault."""
import argparse,json,subprocess,sys
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--states',type=int,nargs='+',default=[0,1,2,3])
    a=p.parse_args();r=a.directory.resolve()
    if not a.states or any(i not in (0,1,2,3) for i in a.states) or len(set(a.states))!=len(a.states):raise ValueError('distinct SRAM states 0..3 required')
    wsldir='/mnt/'+r.drive[0].lower()+r.as_posix()[2:]
    script='''import json,subprocess
from pathlib import Path
r=Path(ROOT)
iv='/tmp/yzl-issue219-iverilog12-20261109/install/bin/iverilog';vv='/tmp/yzl-issue219-iverilog12-20261109/install/bin/vvp'
def run(args,name,negative=None):
    with (r/name).open('xb') as f:p=subprocess.run(args,cwd=r,stdout=f,stderr=subprocess.STDOUT)
    if negative:
        if p.returncode==0 or negative.encode() not in (r/name).read_bytes():raise RuntimeError('wrong-row fault was not detected')
    elif p.returncode:raise RuntimeError('batch program failed '+name)
    return {'returncode':p.returncode,'bytes':(r/name).stat().st_size}
result={'build':run([iv,'-g2012','-Irtl/block_v2','-s','tb_resident_probe','-o','probe.vvp','-f','compile.f'],'build.log')}
for i in STATES:result[str(i)]=run([vv,'probe.vvp','+sinit='+str(i)],'simulate-'+str(i)+'.log')
result['negative']=run([vv,'probe.vvp','+sinit=3','+badrow'],'negative.log','resident M result mismatch')
(r/'run-result.json').write_text(json.dumps(result,indent=2)+'\\n');print(json.dumps(result))
'''.replace('ROOT',repr(wsldir)).replace('STATES',repr(a.states))
    with (r/'wsl-run.log').open('xb') as f:child=subprocess.run(['wsl.exe','--exec',
        '/tmp/yzl-issue219-python3128-20261109/install/bin/python3.12','-B','-c',script],stdout=f,stderr=subprocess.STDOUT)
    if child.returncode:print(repr((r/'wsl-run.log').read_bytes()[-3000:]));raise SystemExit(child.returncode)
    sys.path.insert(0,str(Path('project/experiments/block_synthesis').resolve()))
    from resident_batch_probe import analyse
    result=[analyse(r,r/f'simulate-{i}.log',i) for i in a.states]
    (r/'analysis.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'cases':[v['cases'] for v in result]}))


if __name__=='__main__':main()
