"""Exact accepted93 gate build/replay; reception independent from simulation producer."""
import argparse,traceback
from common import *
from admission93 import admit,SOURCE,INPUT

def main():
 p=argparse.ArgumentParser();p.add_argument('task',choices=['build','sim']);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--build',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--stall',type=int,choices=[0,1],default=0);p.add_argument('--seconds',type=int,default=1100);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);m={'status':'ERROR','source':sources(),'task':a.task,'stall':a.stall,'resources':resource_snapshot()}
 try:
  ad=admit();pm=artifacts(a.prepared);need(pm['status']=='EXACT_ACCEPTED93_GATE_EXPORT_AND_DECLARED_MEMORY_CUT'and load(a.prepared/'admission.json')==ad,'exact accepted prepared source')
  m.update(prepared_directory=str(a.prepared),prepared_manifest_sha256=sha(a.prepared/'manifest.json'),admission=ad)
  if a.task=='build':
   command(a.out,'build',['/eda/verilator-5.042/bin/verilator','--cc','--exe','--build','-j','8','-Wno-fatal','--top-module','chain93','--prefix','Vchain93','--Mdir',a.out/'obj','--output-split','15000','--output-split-cfuncs','200','-CFLAGS','-std=c++17 -O2',a.prepared/'mapped.v',a.prepared/'cells.v',SOURCE/'project/rtl/norm_service/store82.sv',a.prepared/'chain_gate.cpp'],a.seconds)
   m.update(status='ACCEPTED93_GATE_BUILT_NOT_EXECUTED',binary_sha256=sha(a.out/'obj/Vchain93'))
  else:
   bm=artifacts(a.build);need(bm['status']=='ACCEPTED93_GATE_BUILT_NOT_EXECUTED'and bm['prepared_manifest_sha256']==sha(a.prepared/'manifest.json'),'exact gate build dependency');need(sha(a.build/'obj/Vchain93')==bm['binary_sha256'],'binary SHA')
   command(a.out,'simulation',[a.build/'obj/Vchain93',INPUT/'vectors93.tsv',a.out/'actual.jsonl',a.stall],a.seconds)
   m.update(status='ACCEPTED93_GATE_EXECUTED_NOT_RECEIVED',build_manifest_sha256=sha(a.build/'manifest.json'),input_manifest_sha256=sha(INPUT/'manifest.json'))
 except Exception as e:m.update(error=str(e),traceback=traceback.format_exc());raise
 finally:manifest(a.out,m)
 print(m['status'])
if __name__=='__main__':main()
