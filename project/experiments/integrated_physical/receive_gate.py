"""Independent accepted93 gate reception with exact, narrow fixture differences."""
import argparse,copy,importlib.util,sys
from common import *
from admission93 import admit,SOURCE,INPUT,R93
sys.path.insert(0,str(ROOT/'project/experiments/electrical_repair'))
from structure import library,certificate,input_loads

def main():
 p=argparse.ArgumentParser();p.add_argument('--prepared',type=Path,required=True);p.add_argument('--build',type=Path,required=True);p.add_argument('--runs',type=Path,nargs=2,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--post-prepared',type=Path);a=p.parse_args();a.out.mkdir(exist_ok=False);bd=sources();ad=admit();pm=artifacts(a.prepared);bm=artifacts(a.build)
 need(pm['status']=='EXACT_ACCEPTED93_GATE_EXPORT_AND_DECLARED_MEMORY_CUT'and load(a.prepared/'admission.json')==ad,'exact original gate input')
 post=None;post_cert=None;dependency_prepared=a.prepared;build_status='ACCEPTED93_GATE_BUILT_NOT_EXECUTED';run_status='ACCEPTED93_GATE_EXECUTED_NOT_RECEIVED'
 if a.post_prepared is not None:
  from post_audit import audit_post
  post_pm,post_cert,post=audit_post(a.prepared,a.post_prepared,a.out/'post-wrapper',ad);dependency_prepared=a.post_prepared;build_status='POSTPHYSICAL93_GATE_BUILT_NOT_EXECUTED';run_status='POSTPHYSICAL93_GATE_EXECUTED_NOT_RECEIVED';need(bm['original_prepared_manifest_sha256']==sha(a.prepared/'manifest.json'),'same postphysical original prepared')
 need(bm['status']==build_status and bm['prepared_manifest_sha256']==sha(dependency_prepared/'manifest.json')and sha(a.build/'obj/Vchain93')==bm['binary_sha256'],'exact executed gate binary')
 spec=importlib.util.spec_from_file_location('independent93',SOURCE/'project/experiments/gamma_stream/verify.py');ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
 cases=load(INPUT/'cases.json');lookup={c['name']:c for c in cases};old=Path(load(INPUT/'manifest.json')['old_root']);refs={}
 for c in cases:
  for cache in (0,1):refs[c['name'],cache]=ref.matrix_reference(old,c,cache)if c['kind']=='chain'else{'x':ref.ints(bytes.fromhex(c['x'])),'gamma':ref.ints(bytes.fromhex(c['gamma']))}
 lib=library(LIB);before=load(a.prepared/'cut-source.json')['modules']['chain93'];after=load(a.prepared/'cut.json')['modules']['chain93'];scope=[n for n,c in before['cells'].items()if c['type']=='$scopeinfo'];need(len(scope)==5,'exact original hierarchy metadata');
 for n in scope:
  need(before['cells'][n]==after['cells'][n]and before['cells'][n]['connections']=={}and before['cells'][n]['port_directions']=={}and before['cells'][n]['parameters']=={'TYPE':'module'},'only matching empty hierarchy metadata omitted');del before['cells'][n];del after['cells'][n]
 cert=post_cert if post is not None else certificate(before,after,lib);need(float(cert['after_area_um2'])<=79600.5,'actual98 area ceiling');put(a.out/'structure.json',cert);put(a.out/'input-loads.json',input_loads(after,lib));results=[];neg=[]
 for stall,run in enumerate(a.runs):
  rm=artifacts(run);need(rm['status']==run_statusand type(rm['stall'])is int and rm['stall']==stall and rm['build_manifest_sha256']==sha(a.build/'manifest.json'),'strict gate run/stall/binary')
  need(rm['prepared_manifest_sha256']==sha(dependency_prepared/'manifest.json')and rm['input_manifest_sha256']==sha(INPUT/'manifest.json')and rm['admission']==ad,'same full source and input contract')
  rows=[load_line(s)for s in(run/'actual.jsonl').read_text().splitlines()];gold=[load_line(s)for s in(R93/f'rtl-s{stall}03/actual.jsonl').read_text().splitlines()];need(len(rows)==len(gold)==51,'all complete consumer/recovery rows')
  outcomes=[];exceptions=0
  for row,g in zip(rows,gold):
   need(row['name']in lookup and type(row['cache'])is int and row['cache']in(0,1),'typed independent case')
   outcomes.append(ref.check(row,lookup[row['name']],refs[row['name'],row['cache']]))
   normalized=copy.deepcopy(row)
   if g['role']=='last-legal-epoch':
    need(row['role']=='gate-last-normal-command'and type(row['epoch'])is int and row['epoch']==2 and g['epoch']==0xffffffff,'exact ordinary command replaces RTL-only terminal injection')
    normalized['role']=g['role'];normalized['epoch']=g['epoch'];exceptions+=1
   need(normalized==g,'every RTL observable exact except declared role/epoch')
  need(exceptions==1,'one fixture exception only')
  proto=load(run/'actual.jsonl.protocol.json');need(type(proto.get('terminal_rejected_edges'))is int and proto['terminal_rejected_edges']==0,'gate terminal injection not tested')
  normalized=copy.deepcopy(proto);normalized['terminal_rejected_edges']=5;ref.protocol(normalized,rows)
  original=load(R93/f'rtl-s{stall}03/actual.jsonl.protocol.json');need(normalized==original,'exact all protocol fields apart from terminal test count')
  for label,edit in [('out',lambda r:r['out'].__setitem__(0,r['out'][0]^1)),('missing',lambda r:r.pop('sum_words')),('bool',lambda r:r.update(gamma_loads=True))]:
   bad=copy.deepcopy(rows[0]);edit(bad);nf=a.out/f'negative-s{stall}-{label}.json';put(nf,bad)
   try:ref.check(load(nf),lookup[rows[0]['name']],refs[rows[0]['name'],rows[0]['cache']])
   except ValueError:neg.append({'path':nf.name,'sha256':sha(nf)})
   else:raise ValueError('persisted malformed gate accepted '+label)
  results.append({'stall':stall,'records':51,'status':'PASS_ALL_COMPLETE_GATE_INTEGER_OUTPUTS_AND_DECLARED_PROTOCOL','outcomes':outcomes,'protocol':proto,'gate_terminal_injection_tested':False,'run_manifest_sha256':sha(run/'manifest.json'),'full_observable_exception':{'role':'gate-last-normal-command','epoch':2,'terminal_rejected_edges':0,'preserved_idle_clock_cadence':True}})
 put(a.out/'receipt.json',{'schema':'gate98-receipt-v1','status':'PASS_POSTPHYSICAL93_COMPLETE_GATES_AND_DECLARED_EPOCH_EXCEPTION'if post is not None else'PASS_ACTUAL93_COMPLETE_GATES_AND_DECLARED_EPOCH_EXCEPTION','postphysical':post,'source':bd,'admission':ad,'prepared_manifest_sha256':sha(a.prepared/'manifest.json'),'build_manifest_sha256':sha(a.build/'manifest.json'),'results':results,'structure':cert,'file_negatives':neg,'limits':['Zero-delay gate simulation and exact original pin certificate, not analog/PVT/CDC signoff.','Gate does not seed epoch DFFs to max; only real93 RTL terminal test and prior92 local control properties remain separate evidence. No inherited full formal93 proof.','store82 is behavioral in simulation; no real SRAM macro or SRAM timing qualification.']})
 print('PASS_POSTPHYSICAL93_COMPLETE_GATES_AND_DECLARED_EPOCH_EXCEPTION'if post is not None else'PASS_ACTUAL93_COMPLETE_GATES_AND_DECLARED_EPOCH_EXCEPTION')
def load_line(s):return __import__('json').loads(s)
if __name__=='__main__':main()
