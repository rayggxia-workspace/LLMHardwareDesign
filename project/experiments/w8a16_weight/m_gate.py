"""Run the real product-port regression on the fresh mapped M gate netlist."""
import argparse,json,os,subprocess,time
from pathlib import Path
from reference_source.native import check,sha,LIB
ROOT=Path(__file__).resolve().parents[3]
def main():
 p=argparse.ArgumentParser();p.add_argument('--mapping',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();check();cpus=len(os.sched_getaffinity(0));assert cpus in(10,12)
 mapped=json.loads((a.mapping/'receipt.json').read_text());assert mapped['passed']and mapped['mapped']and mapped['top']=='m_native_leaf_s32'
 for path,digest in mapped['source_sha256'].items():assert sha(ROOT/path)==digest
 for path,digest in mapped['reused_artifacts']['artifacts'].items():assert sha(Path(path))==digest
 a.out.mkdir(parents=True,exist_ok=False);r=dict(passed=False,commands=[],source_mapping_sha256=sha(a.mapping/'receipt.json'),start_unix=time.time())
 def run(cmd,log):
  cmd=list(map(str,cmd));start=time.time()
  with(a.out/log).open('w')as f:result=subprocess.run(cmd,cwd=a.out,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT)
  r['commands'].append(dict(command=cmd,log=log,sha256=sha(a.out/log),returncode=result.returncode,seconds=time.time()-start));assert result.returncode==0,log
 try:
  (a.out/'cells.ys').write_text(f'read_liberty -ignore_miss_func -ignore_miss_dir {LIB}\nwrite_verilog -noattr cells.v\n');run(['yosys','-s',a.out/'cells.ys'],'cells.log')
  script=ROOT/'project/experiments/w8a16_weight';run(['python3',script/'codec.py','--source',ROOT,'--out',a.out/'vectors','--check-model-sha'],'codec.log');run(['python3',script/'leaf_vectors.py',a.out/'vectors'],'oracle.log')
  run(['python3',script/'leaf_check.py','--source',ROOT,'--out',a.out/'regression','--vectors',a.out/'vectors','--verilator','/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator','--jobs',cpus,'--signal-netlist',a.mapping/'mapped.v','--cells',a.out/'cells.v'],'regression.log')
  result=json.loads((a.out/'regression/result.json').read_text());assert result['passed'];r.update(passed=True,runs=result['runs'],scope='Fresh mapped standard-cell product M, actual numerical and bounded protocol replay; not final ODB or timed gate simulation')
 finally:
  r['end_unix']=time.time();r['outputs']={str(f.relative_to(a.out)):sha(f)for f in a.out.rglob('*')if f.is_file()};(a.out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
