"""Fetch only small immutable reports; record source hashes and real failures."""
from pathlib import Path
import subprocess,json,hashlib,base64,csv
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'work/YUZE-LU/157';REMOTE='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture'
def get(attempt,name):
    path=REMOTE+'/'+attempt+'/'+name
    code='import pathlib,hashlib,json,base64; p=pathlib.Path('+repr(path)+'); b=p.read_bytes(); print(json.dumps(dict(sha256=hashlib.sha256(b).hexdigest(),data=base64.b64encode(b).decode())))'
    import shlex
    response=subprocess.check_output(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','python3 -c '+shlex.quote(code)])
    obj=json.loads(response);data=base64.b64decode(obj['data']);assert hashlib.sha256(data).hexdigest()==obj['sha256']
    dest=OUT/'evidence'/attempt/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    return dict(remote=path,local=dest.relative_to(ROOT).as_posix(),sha256=obj['sha256'],bytes=len(data))
def main():
    rows=[]
    for attempt,files in {
        'attempt001':['results/queue-state.json','results/A0-rtl/receipt.json','results/A1-rtl/receipt.json','results/A2-rtl/receipt.json','results/controls/receipt.json'],
        'attempt002':['slurm.err','results/compile.log'],
        'attempt003':['results/SYSTEMC_RESULTS.csv','results/environment.json','results/corpus/MANIFEST.json','slurm.out','slurm.err'],
        'attempt004':['slurm.err','results/block_v1_r/build.log'],
        'attempt005':['results/SYSTEMC_RESULTS.csv','results/environment.json','results/corpus/MANIFEST.json','slurm.out','slurm.err'],
        'attempt006':['results/RTL_CORPUS_RESULTS.json','results/M-s32-probe.log','slurm.out','slurm.err'],
    }.items():
        for name in files:rows.append(get(attempt,name))
    for attempt in range(1,8):
        receipt=ROOT/f'.local/157/deployment{attempt:03}.json'
        if receipt.exists():
            dest=OUT/'evidence'/f'deployment{attempt:03}.json';dest.write_bytes(receipt.read_bytes());rows.append(dict(local=dest.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),bytes=dest.stat().st_size))
    results=[]
    for attempt in ('attempt003','attempt005'):
        with(OUT/'evidence'/attempt/'results/SYSTEMC_RESULTS.csv').open()as f:
            for row in csv.DictReader(f):
                row['workload']=row['workload'].split('/')[-1];row['attempt']=attempt;row['validation_scope']='integer_match_and_serialized_policy_only';results.append(row)
    columns=list(dict.fromkeys(k for row in results for k in row))
    with(OUT/'SYSTEMC_RESULTS.csv').open('w',newline='')as f:
        writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader();writer.writerows({k:row.get(k)if row.get(k)is not None else'未测'for k in columns}for row in results)
    manifest=OUT/'EVIDENCE.json';manifest.write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps(dict(files=len(rows),systemc_rows=len(results))))
if __name__=='__main__':main()
