"""Actual postphysical netlist with independently checkable behavioral store wrapper."""
import argparse,re,traceback
from common import *
from admission93 import admit,SOURCE,INPUT

def main():
 p=argparse.ArgumentParser();p.add_argument('task',choices=['prepare','build','sim']);p.add_argument('--original',type=Path,required=True);p.add_argument('--stage',type=Path);p.add_argument('--receipt',type=Path);p.add_argument('--prepared',type=Path);p.add_argument('--build',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--stall',type=int,choices=[0,1],default=0);p.add_argument('--seconds',type=int,default=1100);a=p.parse_args();a.out.mkdir(exist_ok=False);m={'status':'ERROR','source':sources(),'task':a.task,'stall':a.stall,'resources':resource_snapshot()}
 try:
  ad=admit();orig=artifacts(a.original);need(orig['status']=='EXACT_ACCEPTED93_GATE_EXPORT_AND_DECLARED_MEMORY_CUT'and load(a.original/'admission.json')==ad,'original complete gate admission');m.update(admission=ad,original_prepared_manifest_sha256=sha(a.original/'manifest.json'))
  if a.task=='prepare':
   sm=artifacts(a.stage);rc=load(a.receipt/'receipt.json');need(sm['stage']in('place','repair','cts','ctsrepair','routerepair','caprepair')and rc['status']in('PASS_RECEPTION_OF_EXECUTED_PHYSICAL_STAGE_NOT_AUTOMATIC_CLOSURE','PASS_RECEPTION_OF_ROUTE_EVIDENCE_NOT_AUTOMATIC_CLOSURE')and rc['result']['stage_manifest_sha256']==sha(a.stage/'manifest.json')and rc['result']['structure']['status']=='PASS_ALL_ORIGINAL_PIN_AND_PORT_FUNCTIONS_AFTER_TRANSPARENT_FOLD'and rc['result']['physical_geometry']['status']=='PASS_INDEPENDENT_SITE_BOUNDS_NO_OVERLAP_AND_ALL_SIGNAL_CONNECTIONS','exact physical netlist and complete graph/geometry reception')
   top=load(a.original/'mapped.json')['modules']['chain93'];cut=load(a.original/'cut-contract.json');core,count=re.subn(r'\bmodule chain93\b','module physical_core',(a.stage/'final.v').read_text(),count=1);need(count==1,'single exact physical core module rename');decl=[]
   for name,pp in top['ports'].items():
    width=len(pp['bits']);decl.append(pp['direction']+' wire '+('['+str(width-1)+':0] 'if width>1 else'')+name)
   extra=cut['ports'];internal=['wire '+('['+str(e['width']-1)+':0] 'if e['width']>1 else'')+e['port']+';'for e in extra];ports=list(top['ports'])+[e['port']for e in extra];connections=','.join('.'+n+'('+n+')'for n in ports);bank=','.join('.'+e['original_pin']+'('+e['port']+')'for e in extra)
   wrapper='module chain93('+','.join(decl)+');\n'+'\n'.join(internal)+'\nphysical_core core('+connections+');\nstore82 frame(.clk(clk),'+bank+');\nendmodule\n';(a.out/'mapped.v').write_text(core+'\n'+wrapper)
   for name in('cells.v','chain_gate.cpp'):(a.out/name).write_bytes((a.original/name).read_bytes())
   raw=load(a.original/'mapped.json');put(a.out/'bank.json',{'modules':{'store82':raw['modules']['store82']}})
   ys=a.out/'wrapper.ys';ys.write_text(f'read_liberty -lib {LIB}\nread_json {a.out}/bank.json\nread_verilog {a.out}/mapped.v\nhierarchy -top chain93\ncheck -assert\nwrite_json {a.out}/wrapper.json\n');command(a.out,'wrapper',['yosys','-s',ys],300)
   m.update(status='EXACT_POSTPHYSICAL93_GATE_EXPORT',physical_stage_directory=str(a.stage),physical_stage_manifest_sha256=sha(a.stage/'manifest.json'),physical_final_verilog_sha256=sha(a.stage/'final.v'),physical_receipt_directory=str(a.receipt),physical_receipt_sha256=sha(a.receipt/'receipt.json'))
  else:
   pm=artifacts(a.prepared);need(pm['status']=='EXACT_POSTPHYSICAL93_GATE_EXPORT'and pm['original_prepared_manifest_sha256']==sha(a.original/'manifest.json')and pm['admission']==ad,'exact postphysical prepared dependency');m.update(prepared_directory=str(a.prepared),prepared_manifest_sha256=sha(a.prepared/'manifest.json'))
   if a.task=='build':
    command(a.out,'build',['/eda/verilator-5.042/bin/verilator','--cc','--exe','--build','-j','8','-Wno-fatal','--top-module','chain93','--prefix','Vchain93','--Mdir',a.out/'obj','--output-split','15000','--output-split-cfuncs','200','-CFLAGS','-std=c++17 -O2',a.prepared/'mapped.v',a.prepared/'cells.v',SOURCE/'project/rtl/norm_service/store82.sv',a.prepared/'chain_gate.cpp'],a.seconds);m.update(status='POSTPHYSICAL93_GATE_BUILT_NOT_EXECUTED',binary_sha256=sha(a.out/'obj/Vchain93'))
   else:
    bm=artifacts(a.build);need(bm['status']=='POSTPHYSICAL93_GATE_BUILT_NOT_EXECUTED'and bm['prepared_manifest_sha256']==sha(a.prepared/'manifest.json')and sha(a.build/'obj/Vchain93')==bm['binary_sha256'],'exact postphysical binary')
    command(a.out,'simulation',[a.build/'obj/Vchain93',INPUT/'vectors93.tsv',a.out/'actual.jsonl',a.stall],a.seconds);m.update(status='POSTPHYSICAL93_GATE_EXECUTED_NOT_RECEIVED',build_manifest_sha256=sha(a.build/'manifest.json'),input_manifest_sha256=sha(INPUT/'manifest.json'))
 except Exception as e:m.update(error=str(e),traceback=traceback.format_exc());raise
 finally:manifest(a.out,m)
 print(m['status'])
if __name__=='__main__':main()
