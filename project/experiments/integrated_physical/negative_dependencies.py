"""Actual persisted gate retarget/type and STA finite/startpoint rejection tests."""
import argparse,copy,os,shutil,csv,io
from common import *
from gate_dependency import checked_post97
from admission97 import admit
from receive_physical import audit
p=argparse.ArgumentParser();p.add_argument('--gate97',type=Path,required=True);p.add_argument('--prepared97',type=Path,required=True);p.add_argument('--physical97',type=Path,required=True);p.add_argument('--other97',type=Path,required=True);p.add_argument('--stage93',type=Path,required=True);p.add_argument('--prepared93',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);ad=admit();gold=checked_post97(a.gate97,a.prepared97,ad,a.physical97);records=[]
def rejected(tag,fn):
 try:fn()
 except ValueError as e:records.append({'case':tag,'reason':str(e)})
 else:raise ValueError('bad actual evidence accepted '+tag)
for tag in ('retarget_physical','protocol_bool_int','empty_results'):
 out=a.out/tag;out.mkdir();q=copy.deepcopy(gold);target=a.physical97
 if tag=='retarget_physical':
  target=a.other97;q['postphysical']['physical_stage_manifest_sha256']=sha(target/'manifest.json');q['postphysical']['physical_final_verilog_sha256']=sha(target/'final.v')
 elif tag=='empty_results':q['results']=[]
 else:
  oldrun=Path(q['results'][0]['run_directory']);run=out/'run';run.mkdir();m=artifacts(oldrun)
  for f in oldrun.iterdir():
   if f.is_file()and f.name!='manifest.json':
    if f.name=='actual.jsonl.protocol.json':shutil.copyfile(f,run/f.name)
    else:os.link(f,run/f.name)
  proto=load(run/'actual.jsonl.protocol.json');need(type(proto['fabric_high_water'])is int and proto['fabric_high_water']==1,'known integer protocol field');proto['fabric_high_water']=True;put(run/'actual.jsonl.protocol.json',proto);manifest(run,m);q['results'][0].update(run_directory=str(run),run_manifest_sha256=sha(run/'manifest.json'),protocol=proto)
 put(out/'receipt.json',q);rejected(tag,lambda:checked_post97(out,a.prepared97,ad,target));records[-1]['receipt_sha256']=sha(out/'receipt.json')
base=a.out/'baseline93';base.mkdir();audit(a.stage93,a.prepared93,base)
for tag in ('infinite_slack','unknown_startpoint'):
 out=a.out/tag;out.mkdir();m=artifacts(a.stage93)
 for f in a.stage93.iterdir():
  if f.is_file()and f.name!='manifest.json':
   if f.name=='setup-load1.tsv':shutil.copyfile(f,out/f.name)
   else:os.link(f,out/f.name)
 f=out/'setup-load1.tsv';rr=list(csv.DictReader(f.read_text().splitlines(),delimiter='\t'));rr[0]['slack'if tag=='infinite_slack'else'startpoint']='Infinity'if tag=='infinite_slack'else'not_an_actual_pin';buf=io.StringIO();w=csv.DictWriter(buf,fieldnames=list(rr[0]),delimiter='\t',lineterminator='\n');w.writeheader();w.writerows(rr);f.write_text(buf.getvalue());manifest(out,m);receive=out/'receive';receive.mkdir();rejected(tag,lambda:audit(out,a.prepared93,receive));records[-1]['manifest_sha256']=sha(out/'manifest.json')
put(a.out/'receipt.json',{'status':'PASS_FIVE_PERSISTED_GATE_DEPENDENCY_AND_TIMING_NEGATIVES','source':sources(),'resources':resource_snapshot(),'baseline_gate_sha256':sha(a.gate97/'receipt.json'),'records':records});print('PASS_FIVE_PERSISTED_GATE_DEPENDENCY_AND_TIMING_NEGATIVES')
