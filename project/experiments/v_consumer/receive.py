"""Independent strict receiver: original tensor oracle, actual protocol, changed-and-rehashed negatives."""
import argparse,copy,json,shutil
from pathlib import Path
from reference import bound,sha,require,reference,check
ROOT=Path(__file__).resolve().parents[3]
NUM={'accepted':50,'errors':11,'restarts':20,'stage_aborts':7,'register_injections':5,'terminal_rejected_edges':36,'control_conflicts':4,'done_conflicts':1,'hard_resets':6,'soft_aborts_actual':12,'fabric_high_water':2}
FLAGS={'same_core_mixed_and_error_recovery','held_done','latched_parameters','actual_production_Q_injection_declared'}
def protocol(p):
 require(set(p)==set(NUM)|FLAGS|{'schema','stale_responses_actual'},'exact protocol keyset');require(p['schema']=='v97-qualification-v1','protocol schema')
 for k,v in NUM.items():require(type(p[k])is int and p[k]==v,'actual protocol '+k+': '+str(p[k]))
 for k in FLAGS:require(type(p[k])is bool and p[k],'typed protocol flag '+k)
 require(type(p['stale_responses_actual'])is int and p['stale_responses_actual']>=3,'actual stale responses')
def sequence(cs,bs):
 return [(c['name'],'mixed',False)for c in cs]+[(b['name'],'numeric-boundary',True)for b in bs]+[(cs[(k+1)%6]['name'],'restart-address-'+str(k),False)for k in range(6)]+[(cs[1]['name'],'restart-mid-overflow',False),(cs[2]['name'],'restart-old-host-delta',False)]+[(cs[k+1]['name'],'restart-metadata-'+str(k),False)for k in range(3)]+[(cs[(k+1)%6]['name'],'restart-stage-'+str(k),False)for k in range(7)]+[(cs[1]['name'],'restart-stale-response',False),(cs[0]['name'],'last-legal-max',False),(cs[5]['name'],'after-coordinated-reset',False)]
def inspect(folder,refs,seq,input_sha):
 m=bound(folder);require(m['status']=='RTL_EXECUTED_NOT_RECEIVED'and m['suite']=='qualification'and m['input_manifest_sha256']==input_sha,'bound qualification run');p=json.loads((folder/'actual.jsonl.protocol.json').read_text());protocol(p);rows=[json.loads(x)for x in(folder/'actual.jsonl').read_text().splitlines()]
 require([(r['name'],r['role'],r['prep_only'])for r in rows]==seq,'all samecore commands exactly once and in order');summary=[check(r,refs[r['name']])for r in rows]
 require(rows[-2]['epoch']==4294967295 and rows[-1]['epoch']==1,'final real command then coordinated reset')
 failures=[json.loads(x)for x in(folder/'actual.jsonl.failures.jsonl').read_text().splitlines()];expected=[('address-config-'+str(k),16)for k in range(6)]+[('MID-overflow',33),('old-host-delta',1)]+[('A-metadata-'+str(k),17)for k in range(3)]
 require([(r['name'],r['status'])for r in failures]==expected,'all actual error paths')
 for r in failures:
  require(set(r)=={'name','status','epoch','transactions','A_published'}and type(r['A_published'])is bool,'error receipt fields')
  if r['name'].startswith('address-config-'):require(r['transactions']==0 and r['A_published']is False,'rejected address has no side effects')
 require(failures[6]['A_published']is False,'overflow not published')
 return m,p,summary,failures
def reseal(folder):
 p=folder/'manifest.json';m=json.loads(p.read_text())
 for e in m['artifacts']:e['bytes']=(folder/e['path']).stat().st_size;e['sha256']=sha(folder/e['path'])
 p.write_text(json.dumps(m,indent=2)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--run',type=Path,required=True);p.add_argument('--build',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);b=json.loads((ROOT/'binding.json').read_text())
 for n,h in b['sources'].items():require(sha(ROOT/n)==h,'receiver frozen source')
 im=bound(a.input);bm=bound(a.build);rm=bound(a.run);require(bm['status']=='BUILT_NOT_EXECUTED'and bm['suite']=='qualification','actual build status');require(sha(a.build/'obj/Vchain97')==bm['binary_sha256'],'actual executed binary')
 for n,h in rm['source']['sources'].items():
  if n.startswith('project/rtl/')or n.endswith(('/sim.cpp','/qualification.cpp')):require(bm['source']['sources'].get(n)==h,'source build/run exact')
 cs=json.loads((a.input/'cases.json').read_text());bs=json.loads((a.input/'boundaries.json').read_text());refs={c['name']:reference(a.input,c)for c in cs+bs};seq=sequence(cs,bs);m,proto,summary,failures=inspect(a.run,refs,seq,sha(a.input/'manifest.json'));negative=[]
 mutants=[('mid',0),('A8',0),('delta',0),('acc',0),('down',0),('joined',0),('out',0)]
 for key,index in mutants:
  dst=a.out/('negative-'+key);shutil.copytree(a.run,dst);p=dst/'actual.jsonl';rows=[json.loads(x)for x in p.read_text().splitlines()];rows[0][key][index]^=1;p.write_text(''.join(json.dumps(x)+'\n'for x in rows));reseal(dst)
  try:inspect(dst,refs,seq,sha(a.input/'manifest.json'))
  except ValueError as e:negative.append({'path':str(dst),'manifest_sha256':sha(dst/'manifest.json'),'rejected':str(e)})
  else:raise ValueError('rehashed semantic corruption accepted')
 for kind in ('wrong-type','missing','extra','wrong-count'):
  dst=a.out/('negative-'+kind);shutil.copytree(a.run,dst);p=dst/'actual.jsonl.protocol.json';bad=json.loads(p.read_text())
  if kind=='wrong-type':bad['held_done']='true'
  elif kind=='missing':del bad['stage_aborts']
  elif kind=='extra':bad['unknown']=True
  else:bad['accepted']-=1
  p.write_text(json.dumps(bad)+'\n');reseal(dst)
  try:inspect(dst,refs,seq,sha(a.input/'manifest.json'))
  except ValueError as e:negative.append({'path':str(dst),'manifest_sha256':sha(dst/'manifest.json'),'rejected':str(e)})
  else:raise ValueError('rehashed protocol corruption accepted')
 result={'status':'PASS_ORIGINAL_V_M_NORM_AND_RECOVERY','receiver_source':b,'source':m['source'],'run_manifest_sha256':sha(a.run/'manifest.json'),'build_manifest_sha256':sha(a.build/'manifest.json'),'input_manifest_sha256':sha(a.input/'manifest.json'),'protocol':proto,'rows':summary,'errors':failures,'rehashed_negatives':negative,'numeric_boundary_deltas':{c['name']:refs[c['name']]['delta']for c in bs},'delta_by_real_case':{c['name']:refs[c['name']]['delta']for c in cs}};(a.out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'])
if __name__=='__main__':main()
