"""Run an already generated continuation probe in the pinned local WSL tools."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def main():
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--attempt',type=int,default=2);a=p.parse_args()
    if a.attempt<1:raise ValueError('positive probe run attempt required')
    directory=a.directory.resolve();wsldir='/mnt/'+directory.drive[0].lower()+directory.as_posix()[2:]
    # This is subprocess argv, not an interpolated shell command.
    code='''import json,subprocess
from pathlib import Path
r=Path(ROOT)
attempt=ATTEMPT
iv="/tmp/yzl-issue219-iverilog12-20261109/install/bin/iverilog"
vv="/tmp/yzl-issue219-iverilog12-20261109/install/bin/vvp"
def run(args,name,negative=False):
    with (r/name).open("xb") as f:p=subprocess.run(args,cwd=r,stdout=f,stderr=subprocess.STDOUT)
    raw=(r/name).read_bytes()
    if negative:
        if p.returncode==0 or b"FATAL" not in raw:raise RuntimeError("negative did not fail: "+name)
    elif p.returncode:raise RuntimeError("probe failed: "+name)
    return {"returncode":p.returncode,"bytes":len(raw)}
result={}
result["build"]=run([iv,"-g2012","-Irtl/block_v2","-s","tb_resident_probe","-o","probe-"+str(attempt)+".vvp","-f","compile.f"],"build-"+str(attempt)+".log")
for i in range(3):result["sinit"+str(i)]=run([vv,"probe-"+str(attempt)+".vvp","+sinit="+str(i)],"simulate-"+str(i)+"-run"+str(attempt)+".log")
base=(r/"compile.f").read_text().splitlines()
for kind in ("guard","bank"):
    result["negative_"+kind+"_build"]=run([iv,"-g2012","-Irtl/block_v2","-s","tb_resident_probe","-o","negative-"+kind+"-"+str(attempt)+".vvp","tb_negative_"+kind+".sv",*base[1:]],"negative-"+kind+"-build-"+str(attempt)+".log")
    result["negative_"+kind]=run([vv,"negative-"+kind+"-"+str(attempt)+".vvp","+sinit=2"],"negative-"+kind+"-"+str(attempt)+".log",True)
(r/("run-result-"+str(attempt)+".json")).write_text(json.dumps(result,indent=2)+"\\n")
print(json.dumps(result))
'''.replace('ROOT',repr(wsldir)).replace('ATTEMPT',str(a.attempt))
    log=directory/('wsl-run-'+str(a.attempt)+'.log')
    with log.open('xb') as f:
        result=subprocess.run(['wsl.exe','--exec','/tmp/yzl-issue219-python3128-20261109/install/bin/python3.12',
                               '-B','-c',code],stdout=f,stderr=subprocess.STDOUT)
    if result.returncode:
        print(repr(log.read_bytes()[-3000:]));raise SystemExit(result.returncode)
    sys.path.insert(0,str(Path('project/experiments/block_synthesis').resolve()))
    from resident_probe import analyse
    reports=[analyse(directory,directory/('simulate-'+str(i)+'-run'+str(a.attempt)+'.log'),write_summary=False) for i in range(3)]
    timing=json.loads((directory/'manifest.json').read_text())['origin_timing']['profile']
    for report in reports:
        for row in report['passive_profiles']:
            if row['min']!=row['max'] or row['max']+1!=timing[row['boundary']][str(row['key'])]:
                raise ValueError('continuation service timing differs from origin qualification')
    record={'passed':True,'cases_per_initialization':[r['cases'] for r in reports],
            'manifest_sha256':reports[0]['manifest_sha256'],'log_sha256':[r['log_sha256'] for r in reports],
            'reports':reports,'negative':json.loads((directory/('run-result-'+str(a.attempt)+'.json')).read_text()),
            'scope':'continuous synthetic source-region native RTL and passive slots; not actual weights/full system/energy/token/s'}
    (directory/('acceptance-'+str(a.attempt)+'.json')).write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if k not in ('reports','negative')}))


if __name__=='__main__':main()
