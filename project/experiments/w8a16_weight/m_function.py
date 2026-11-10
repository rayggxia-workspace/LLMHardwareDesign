"""Replay actual-model M projection records through actual final-ODB signal netlist."""
import argparse,json,os,subprocess,sys,time
from pathlib import Path
from reference_source.native import check as check_native,sha,LIB
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'project/experiments/block_v2'))
from qualify import source
from native_signal_view import export

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 check_native();cpus=len(os.sched_getaffinity(0));assert cpus in (10,12)
 folder,original,flow,results=source(a.source);assert flow['top']=='m_native_leaf_s32';a.out.mkdir(parents=True,exist_ok=False)
 receipt=dict(passed=False,source_receipt_sha256=sha(folder/'receipt.json'),commands=[],start_unix=time.time())
 def run(command,log):
  command=list(map(str,command));start=time.time()
  with(a.out/log).open('w')as stream:r=subprocess.run(command,cwd=a.out,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT)
  receipt['commands'].append(dict(command=command,log=log,sha256=sha(a.out/log),returncode=r.returncode,seconds=time.time()-start));assert r.returncode==0,(log,r.returncode)
 try:
  netlist,proof=export(ROOT,a.out,run,folder,original,results,'m_native_leaf_s32',LIB)
  (a.out/'cells.ys').write_text(f'read_liberty -ignore_miss_func -ignore_miss_dir {LIB}\nwrite_verilog -noattr cells.v\n');run(['yosys','-s',a.out/'cells.ys'],'cells.log')
  scripts=ROOT/'project/experiments/w8a16_weight'
  run(['python3',scripts/'codec.py','--source',ROOT,'--out',a.out/'vectors','--check-model-sha'],'codec.log')
  run(['python3',scripts/'leaf_vectors.py',a.out/'vectors'],'oracle.log')
  run(['python3',scripts/'leaf_check.py','--source',ROOT,'--out',a.out/'regression','--vectors',a.out/'vectors','--verilator','/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator','--jobs',cpus,'--signal-netlist',netlist,'--cells',a.out/'cells.v'],'regression.log')
  tests=json.loads((a.out/'regression/result.json').read_text());assert tests['passed']and len(tests['runs'])==3
  report=dict(passed=True,source_receipt_sha256=sha(folder/'receipt.json'),full_final_netlist=proof,final_odb_sha256=sha(results/'6_final.odb'),runs=tests['runs'],oracle=json.loads((a.out/'vectors/leaf-manifest.json').read_text()),actual_public_records=34,scope='Actual final ODB complete signal-bearing M leaf, original protection loads retained; real public W bytes and FP16 scales, 3 initial states, finite MC/A/guard backpressure, negative transport, RF snapshot strict real ACK. Host S provider, not an entire Qwen model or LC production bridge.')
  (a.out/'final-function.json').write_text(json.dumps(report,indent=2)+'\n');receipt['passed']=True
 finally:
  receipt['end_unix']=time.time();receipt['outputs']={str(q.relative_to(a.out)):sha(q)for q in a.out.rglob('*')if q.is_file()};(a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
