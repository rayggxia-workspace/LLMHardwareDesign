"""Corpus vs frozen RTL; exact wide multiply decomposition measured on M."""
from pathlib import Path
import subprocess,json,concurrent.futures,os,argparse,hashlib
P=Path(__file__).resolve().parent;ROOT=P.parents[2];INPUT=ROOT/'work/YUZE-LU/157/inputs'
def run(cmd,log):
    with log.open('w')as f:p=subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,timeout=7200)
    assert p.returncode==0,(str(log),p.returncode)
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--corpus',required=True,type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    os.environ['VERILATOR_ROOT']='/public/home/yuzelu/opt/eda/verilator-5.042/share/verilator'
    verilator='/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator'
    def build(top,src,bench):
        folder=a.out/top;folder.mkdir()
        run([verilator,'--cc','--exe','--build','-j','8','--output-groups','0','-Wno-fatal','--top-module',top,'-CFLAGS','-O1','--Mdir',folder/'obj',src,P/bench],folder/'build.log');return folder/'obj'/('V'+top)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
        r=pool.submit(build,'block_v1_r',INPUT/'block_v1_r.sv','corpus_rtl.cpp');m=pool.submit(build,'block_v2_m',INPUT/'block_v2_m.sv','m_s32_probe.cpp');rbin=r.result();mbin=m.result()
    run([mbin],a.out/'M-s32-probe.log')
    manifest=json.loads((a.corpus/'MANIFEST.json').read_text());rows=[]
    def check(case):
        path=a.corpus/case['path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==case['sha256'];log=a.out/(path.stem+'.log');run([rbin,path],log)
        result=[json.loads(x)for x in log.read_text().splitlines()if x.startswith('{')];assert len(result)==1
        return dict(workload=case['path'],input_sha256=case['sha256'],**result[0])
    with concurrent.futures.ThreadPoolExecutor(max_workers=8)as pool:
        futures=[pool.submit(check,case)for case in manifest['cases']]
        for f in concurrent.futures.as_completed(futures):rows.append(f.result());(a.out/'RTL_CORPUS_RESULTS.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps(dict(corpus_cases=len(rows),pass_cases=sum(x['status']=='PASS'for x in rows))))
if __name__=='__main__':main()
