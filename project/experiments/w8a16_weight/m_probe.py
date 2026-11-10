"""Read-only OpenDB diagnostics for an owned failed M physical run, on Slurm."""
import argparse,json,os,subprocess
from pathlib import Path
from reference_source.native import check,sha,LIB

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();check();assert len(os.sched_getaffinity(0))in(10,12);a.out.mkdir(parents=True,exist_ok=False)
 dbs=sorted((a.run/'flow/results/nangate45/bv1_m_native_leaf_s32/base').glob('*.odb'));assert dbs
 receipts=[]
 for index,path in enumerate(dbs):
  script='read_liberty '+str(LIB)+'\nread_db '+str(path)+'\nputs {DB '+path.name+'}\n'
  script+='''set block [ord::get_db_block]
foreach net [$block getNets] {
 set name [$net getName]
 if {$name ni {one_ zero_ VDD VSS} && [$net getSigType] ni {POWER GROUND}} {continue}
 puts "NET $name type=[$net getSigType] special=[$net isSpecial] iterms=[llength [$net getITerms]] bterms=[llength [$net getBTerms]] swires=[llength [$net getSWires]]"
 set count 0
 foreach term [$net getITerms] {
  puts " TERM [[$term getInst] getName]/[[$term getMTerm] getName] master=[[[$term getInst] getMaster] getName] io=[[$term getMTerm] getIoType] type=[[$term getMTerm] getSigType]"
  incr count
  if {$count>=12} {break}
 }
}
'''
  tcl=a.out/(path.stem+'.tcl');log=a.out/(path.stem+'.log');tcl.write_text(script)
  with log.open('w')as f:r=subprocess.run(['openroad','-exit',tcl],stdout=f,stderr=subprocess.STDOUT)
  receipts.append(dict(database=str(path),SHA256=sha(path),returncode=r.returncode,script_SHA256=sha(tcl),log_SHA256=sha(log)))
 receipt=dict(passed=all(x['returncode']==0 for x in receipts),runs=receipts,scope='Read-only native database PG/constant-net diagnostics; no physical repair or acceptance')
 (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');assert receipt['passed'];print(json.dumps(receipt))
if __name__=='__main__':main()
