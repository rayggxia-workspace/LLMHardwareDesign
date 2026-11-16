"""Run actual concurrent native traces and the early-ACK fault injection."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def main():
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();r=a.directory.resolve()
    wsldir='/mnt/'+r.drive[0].lower()+r.as_posix()[2:]
    code='''import json,subprocess
from pathlib import Path
r=Path(ROOT)
iv="/tmp/yzl-issue219-iverilog12-20261109/install/bin/iverilog"
vv="/tmp/yzl-issue219-iverilog12-20261109/install/bin/vvp"
def run(args,name,negative=None):
    with (r/name).open("xb") as f:p=subprocess.run(args,cwd=r,stdout=f,stderr=subprocess.STDOUT)
    raw=(r/name).read_bytes()
    if negative:
        if p.returncode==0 or negative.encode() not in raw:raise RuntimeError("wrong negative: "+name)
    elif p.returncode:raise RuntimeError("probe failed: "+name)
    return {"returncode":p.returncode,"bytes":len(raw)}
result={}
result["build"]=run([iv,"-g2012","-Irtl/block_v2","-s","tb_resident_probe","-o","probe.vvp","-f","compile.f"],"build.log")
for i in range(3):result["sinit"+str(i)]=run([vv,"probe.vvp","+sinit="+str(i)],"simulate-"+str(i)+".log")
base=(r/"compile.f").read_text().splitlines()
result["ack_build"]=run([iv,"-g2012","-Irtl/block_v2","-s","tb_resident_probe","-o","ack.vvp","tb_negative_ack.sv",*base[1:]],"ack-build.log")
result["ack"]=run([vv,"ack.vvp","+sinit=2"],"ack.log","LOAD before STORE committed")
(r/"run-result.json").write_text(json.dumps(result,indent=2)+"\\n")
print(json.dumps(result))
'''.replace('ROOT',repr(wsldir))
    with (r/'wsl-run.log').open('xb') as f:
        result=subprocess.run(['wsl.exe','--exec','/tmp/yzl-issue219-python3128-20261109/install/bin/python3.12','-B','-c',code],stdout=f,stderr=subprocess.STDOUT)
    if result.returncode:print(repr((r/'wsl-run.log').read_bytes()[-2500:]));raise SystemExit(result.returncode)
    sys.path.insert(0,str(Path('project/experiments/block_synthesis').resolve()))
    from resident_overlap_probe import analyse_overlap
    reports=[analyse_overlap(r,r/f'simulate-{i}.log') for i in range(3)]
    manifest=json.loads((r/'manifest.json').read_text());timing=manifest['origin_timing']['profile']
    for report in reports:
        for row in report['passive_profiles']:
            if row['min']!=row['max'] or row['max']+1!=timing[row['boundary']][str(row['key'])]:
                raise ValueError('concurrent native service timing differs from origin')
    acceptance={'passed':True,'cases_per_initialization':[p['cases'] for p in reports],
        'native_overlap_cycles':[p['native_overlap_cycles'] for p in reports],
        'manifest_sha256':reports[0]['manifest_sha256'],'log_sha256':[p['log_sha256'] for p in reports],
        'reports':reports,'negative':json.loads((r/'run-result.json').read_text()),
        'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'scope':manifest['scope'],'excluded':manifest['excluded']}
    (r/'acceptance.json').write_text(json.dumps(acceptance,indent=2)+'\n')
    print(json.dumps({k:v for k,v in acceptance.items() if k not in ('reports','negative')}))


if __name__=='__main__':main()
