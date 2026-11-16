"""Execute native multi-row service qualification and a row-index fault."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


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
    data=(r/name).read_bytes()
    if negative:
        if p.returncode==0 or negative.encode() not in data:raise RuntimeError('wrong fault result '+name)
    elif p.returncode:raise RuntimeError('row probe failed '+name)
    return {'returncode':p.returncode,'bytes':len(data)}
results={}
results['build']=run([iv,'-g2012','-Irtl/block_v2','-s','tb_resident_row_probe','-o','probe.vvp','-f','compile.f'],'build.log')
for i in range(3):results['sinit'+str(i)]=run([vv,'probe.vvp','+sinit='+str(i)],'simulate-'+str(i)+'.log')
original=(r/'tb_resident_row_probe.sv').read_text()
wrong=original.replace('command(5,rr<<3,','command(5,0,')
if wrong==original:raise RuntimeError('row-index fault was not injected')
(r/'tb_negative_row.sv').write_text(wrong)
files=(r/'compile.f').read_text().splitlines()
results['negative_build']=run([iv,'-g2012','-Irtl/block_v2','-s','tb_resident_row_probe','-o','negative.vvp','tb_negative_row.sv',*files[1:]],'negative-build.log')
results['negative']=run([vv,'negative.vvp','+sinit=2'],'negative.log','row result differs')
(r/'run-result.json').write_text(json.dumps(results,indent=2)+'\\n')
print(json.dumps(results))
'''.replace('ROOT',repr(wsldir))
    with (r/'wsl-run.log').open('xb') as f:
        child=subprocess.run(['wsl.exe','--exec','/tmp/yzl-issue219-python3128-20261109/install/bin/python3.12','-B','-c',script],stdout=f,stderr=subprocess.STDOUT)
    if child.returncode:print(repr((r/'wsl-run.log').read_bytes()[-2000:]));raise SystemExit(child.returncode)
    sys.path.insert(0,str(Path('project/experiments/block_synthesis').resolve()))
    from resident_row_probe import qualification
    result=qualification(r,[r/f'simulate-{i}.log' for i in range(3)])
    (r/'qualification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':True,'proof':result['proof'],'formats':result['formats']}))


if __name__=='__main__':main()
