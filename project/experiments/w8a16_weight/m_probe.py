"""Read-only OpenDB diagnostics for an owned failed M physical run, on Slurm."""
import argparse,json,os,subprocess
from pathlib import Path
from reference_source.native import check,sha,LIB

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--timing-db',type=Path);a=p.parse_args();check();assert len(os.sched_getaffinity(0))in(10,12);a.out.mkdir(parents=True,exist_ok=False)
 if a.timing_db:
  assert a.timing_db.is_file() and a.timing_db.is_relative_to(a.run)
  sdc=a.run/'input.sdc';assert sdc.is_file()
  script='read_liberty '+str(LIB)+'\nread_db '+str(a.timing_db)+'\nread_sdc '+str(sdc)+'\n'
  script+='source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl\nestimate_parasitics -placement\n'
  script+='report_checks -path_delay max -group_path_count 12 -endpoint_path_count 1 -fields {slew cap fanout input_pins} -digits 4\n'
  for port in ('a_ready','lc_ready','mc_rsp_ready'):
   script+='puts {EXACT_OUTPUT '+port+'}\nreport_checks -to [get_ports '+port+'] -path_delay max -group_path_count 4 -fields {slew cap fanout input_pins} -digits 4\n'
  for port in ('mc_rsp_tag*','lc_data*','a_session*'):
   script+='puts {EXACT_INPUT '+port+'}\nreport_checks -from [get_ports '+port+'] -path_delay max -group_path_count 4 -fields {slew cap fanout input_pins} -digits 4\n'
  tcl=a.out/'timing.tcl';log=a.out/'timing.log';tcl.write_text(script)
  with log.open('w')as f:r=subprocess.run(['openroad','-exit',tcl],stdout=f,stderr=subprocess.STDOUT)
  receipt=dict(passed=r.returncode==0,database=str(a.timing_db),database_SHA256=sha(a.timing_db),SDC_SHA256=sha(sdc),script_SHA256=sha(tcl),log_SHA256=sha(log),scope='Read-only original-300MHz placement-RC path diagnosis; NOT final extracted qualification')
  (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');assert receipt['passed'];print(json.dumps(receipt));return
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
