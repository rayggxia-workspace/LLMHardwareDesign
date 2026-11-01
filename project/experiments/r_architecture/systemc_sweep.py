"""Independent clocked model compile, fixed corpus and bounded dynamic queue."""
from pathlib import Path
import argparse,subprocess,concurrent.futures,json,hashlib,csv,time,os
P=Path(__file__).resolve().parent
INSTALL=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153/install')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--sweep',action='store_true');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    assert digest(INSTALL/'lib64/libsystemc.so.3.0.1')=='930767c0ec7a203c38552201a22fa2a27a319c47d4d9019096457a674bca0848'
    compile_cmd=['g++','-std=c++17','-O2','-Wall','-Wextra',str(P/'systemc.cpp'),'-I'+str(INSTALL/'include'),'-L'+str(INSTALL/'lib64'),'-Wl,-rpath,'+str(INSTALL/'lib64'),'-lsystemc','-pthread','-o',str(a.out/'model')]
    with(a.out/'compile.log').open('w')as f:subprocess.run(compile_cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
    subprocess.run(['python3',str(P/'workloads.py'),'--out',str(a.out/'corpus')],check=True)
    manifest=json.loads((a.out/'corpus/MANIFEST.json').read_text());jobs=[]
    for case in manifest['cases']:
        for arch,cap in [('A0',2048),('B256',256),('B512',512),('B1024',1024),('B2048',2048),('C',0)]:
            for latency,bw in ([(20,16),(100,16),(20,4),(100,4)]if a.sweep else[(20,16)]):jobs.append((case['path'],arch,cap,latency,bw))
    def run(row):
        name,arch,cap,latency,bw=row;tag=f'{Path(name).stem}-{arch}-L{latency}-B{bw}';out=a.out/(tag+'.csv');log=a.out/(tag+'.log');start=time.time()
        cmd=[str(a.out/'model'),str(a.out/'corpus'/name),arch,str(cap),str(latency),str(bw),str(out),'157']
        with log.open('w')as f:process=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=1800)
        return dict(tag=tag,command=cmd,exit_code=process.returncode,seconds=time.time()-start,csv_sha256=digest(out)if out.exists()else None)
    receipts=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8)as pool:
        futures=[pool.submit(run,x)for x in jobs]
        for future in concurrent.futures.as_completed(futures):
            receipts.append(future.result());(a.out/'receipts.json').write_text(json.dumps(receipts,indent=2)+'\n')
    rows=[]
    for item in receipts:
        assert item['exit_code']==0,item
        with(a.out/(item['tag']+'.csv')).open()as f:rows+=list(csv.DictReader(f))
    with(a.out/'SYSTEMC_RESULTS.csv').open('w',newline='')as f:
        writer=csv.DictWriter(f,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
    (a.out/'environment.json').write_text(json.dumps(dict(compile=compile_cmd,source_sha256=digest(P/'systemc.cpp'),oracle_sha256=digest(P/'workloads.py'),systemc_sha256=digest(INSTALL/'lib64/libsystemc.so.3.0.1'),jobs=len(jobs),policy='Serialized DMA, narrow S only. No optimal-overlap or final architecture recommendation claim.',area='未测',energy='uncalibrated; events only'),indent=2)+'\n')
    print(json.dumps(dict(jobs=len(jobs),passed=sum(x['status']=='PASS'for x in rows),unsupported=sum(x['status']!='PASS'for x in rows))))
if __name__=='__main__':main()
