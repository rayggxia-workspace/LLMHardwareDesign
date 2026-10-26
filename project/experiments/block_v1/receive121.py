# Derived math receiver SHA256 8d851d68649108e69c2233dbb89d568a5a04e14bc91f1e42e8e25c01102ef1ec
"""Independent complete integer receiver; mathematical checks derived unchanged except elapsed T drain."""
import argparse,hashlib,importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'project/experiments/shared_gdn'))
import receive as upstream
from gverify import GNUMBERS,GSTRINGS,GARRAYS
Oracle=upstream.Oracle
need=upstream.need
sha=upstream.sha
ARRAYS=upstream.ARRAYS
STRINGS=upstream.STRINGS
NUMBERS=upstream.NUMBERS|{'sink_drain_cycles'}
QUAL_ROLES=upstream.QUAL_ROLES
CHECKS=upstream.CHECKS

def inspect(inp,run,oracle):
 m=json.loads((run/'manifest.json').read_text())
 need(m['schema']=='shared121-committed-run/1' and m['suite']=='mixed-committed','new top actual run')
 source_bundle=json.loads((ROOT/'bundle-manifest.json').read_text())
 need(m['source_commit']==source_bundle['source_commit'] and m['source_bundle_sha256']==sha(ROOT/'bundle-manifest.json'),'exact source bundle')
 for e in source_bundle['files']:need(sha(ROOT/e['path'])==e['sha256'],'receiver/driver/RTL scientific source')
 need(sha(m['build_path'])==m['build_sha256'],'actual build identity')
 build=json.loads(Path(m['build_path']).read_text())
 need(build['top']=='shared121' and build['binary_sha256']==m['binary_sha256'] and build['source_commit']==m['source_commit'],'correct top and compiled source')
 command=json.loads((run/'simulation-command.json').read_text())
 need(command['exit']==0 and sha(command['argv'][0])==m['binary_sha256'],'exact executed new binary')
 need(command['argv'][1:]==[str(inp/'vectors.tsv'),str(run/'actual.jsonl'),str(m['stall']),str(m['pilot'])],'exact input and wait mode')
 need(sha(inp/'manifest.json')==m['input_manifest_sha256'],'original scientific input binding')
 for artifact in m['artifacts']:
  p=(run/artifact['path']).resolve()
  need(p.is_relative_to(run.resolve()) and p.stat().st_size==artifact['bytes'] and sha(p)==artifact['sha256'],'run actual artifact')
 rows=[json.loads(x)for x in(run/'actual.jsonl').read_text().splitlines()];qual=m['suite']=='qualification';roles=QUAL_ROLES if qual else ['init','G-restore-native','mixed-M0','G-native0','mixed-Afull','mixed-R0']+([]if m['pilot']else['G-native1','mixed-Acached','mixed-M5','mixed-R1','G-native2'])+['G-restore-rescale','G-actual-rescale'];need([x['role']for x in rows]==roles,'exact predeclared order')
 state=[0]*32768;y=[0]*128;unit=oracle.unit;epoch=0;pos=0;bank=0;reg_version=0;reg_length=0;prev_transport=0;summary=[]
 oracle.g.prepare(run,rows)
 for index,row in enumerate(rows):
  need(set(row)==ARRAYS|STRINGS|NUMBERS|GNUMBERS|GSTRINGS|GARRAYS,'exact row keys')
  for k in NUMBERS|GNUMBERS:need(type(row[k])is int and (-(1<<63)if k=='r_unit'else 0)<=row[k]<(1<<64),'typed integer '+k)
  for k in STRINGS|GSTRINGS:need(type(row[k])is str,'typed string '+k)
  for k in ARRAYS|GARRAYS:need(type(row[k])is list and all(type(v)is int for v in row[k]),'integer array '+k)
  role=row['role'];kind=row['kind'];status=row['status'];expected_status=2 if role.startswith('abort-')else 17 if role in('same-version-scale','old-version-after-R','owner-after-R')else 3 if role in('reject-R','reject-G')else 4 if role.startswith('G-bad-')else 0
  need(status==expected_status,'expected status');need(row['wire_beats']==row['transactions']*5,'actual five128bit beats');need(row['result_lines']*(2 if row['kind']==3 else 4)==len(row['g_out']if row['kind']==3 else row['out']),'actual export all words');need(row['cycles']+1+row['sink_drain_cycles']==row['elapsed'],'command to held done elapsed');need(row['cycles']>=row['export_cycles']+row['drain_cycles'],'disjoint D phases')
  expected_transport=0xffffffff if role in('terminal-max','G-terminal-max')else 1 if role in('after-reset-restore','second-reset-Rrestore')else prev_transport+1;need(row['epoch']==expected_transport,'actual no-wrap epoch sequence');prev_transport=expected_transport
  if role in('after-reset-restore','second-reset-Rrestore'):reg_version=reg_length=0
  if kind==0:
   need(row['name']in oracle.m,'selected original M');ref=oracle.m[row['name']]
   for k in ['mid','A8','acc','down','joined','out']:
    need(row[k]==ref[k][:len(row[k])]and(status!=0 or len(row[k])==len(ref[k])),'independent M '+k)
   if status==0:
    need(row['delta']==ref['delta']and row['sum_hex']==ref['sum_hex']and row['den_hex']==ref['den_hex'],'actual M scales/norm');need((row['mul0'],row['mul1'])==(26112,7168),'M shared S32 traffic');need(row['transactions']==2048+ref['lut_reads']+405504+384,'M external traffic');need(row['result_lines']==384,'M full export');need(row['fgrants']==1538,'M shared SFU');need(row['sreads']==395776 and row['swrites']==2432,'M actual S includes result export')
   need(not any(row[k]for k in ['qk','score','exp','sum','P','state','committed_y']),'M exact observation domain')
  elif kind==1:
   need(row['name']in oracle.a,'selected original A');spec,ref,eligible=oracle.a[row['name']]
   for k,v in ref.items():need(row[k]==v[:len(row[k])]and(status!=0 or len(row[k])==len(v)),'independent A '+k)
   need(not any(row[k]for k in ['mid','A8','delta','acc','down','joined','state','committed_y']),'A exact observation domain')
   if status==0:
    n=spec['length'];need(row['transactions']==256*n+2*eligible and row['mul0']==8*n and row['mul1']==0 and row['fgrants']==eligible,'A shared traffic');need(row['result_lines']==256,'A full export');need(row['sreads']==384*n+16*((n+3)//4)+128*((n+7)//8)+256*((n+15)//16-1)+256 and row['swrites']==256*n+8*((n+3)//4)+8*((n+7)//8)+256*((n+15)//16),'A actual S includes result export')
   if status==17:need(row['transactions']==row['mul0']==row['mul1']==row['fgrants']==row['sreads']==row['swrites']==row['result_lines']==0,'metadata rejection no service effects')
   if status!=17:
    reg_version=(4 if role in('recover-stale','terminal-max')else 3 if role=='later-Acached'else 1 if role in('initial-A','mixed-Afull','after-reset-A')else 2);reg_length=spec['length']
  elif kind==2:
   need(kind==2 and row['name']=='head0','exact R head');need(not any(row[k]for k in ['mid','A8','delta','acc','down','joined','qk','score','exp','sum','P']),'R exact observation domain')
   if role=='init':need(row['transactions']==8225 and row['root_writes']==1 and row['result_lines']==0,'actual full state INIT')
   elif role in('after-reset-restore','second-reset-Rrestore'):need(row['transactions']==1 and row['root_writes']==0 and row['result_lines']==0,'actual RESTORE root read')
   elif status==0:
    (state,y,unit,epoch,retries),alpha=oracle.rstep(state,unit,epoch,pos);pos+=1;bank^=1
    need(row['out']==y and row['r_retries']==retries,'full R candidate');need(row['transactions']==73923+40960*retries and row['mul0']==(98688 if alpha!=(1<<31)else 65920)+retries*(65792 if alpha!=(1<<31)else 33024)and row['mul1']==0,'R shared traffic');need(row['root_writes']==1 and row['result_lines']==32,'one R atomic root commit');need(row['sreads']==148000+82304*retries and row['swrites']==33026+24640*retries,'R full state/proposal/consumer finite S traffic')
   else:
    need(row['root_writes']==0,'failed R never publishes root')
    if status==3:(trial,yy,uu,ee,retries),alpha=oracle.rstep(state,unit,epoch,pos);need(row['out']==yy and row['result_lines']==32,'rejected true candidate')
   need(row['state']==state and row['committed_y']==y,'full32768 state and128Y independent')
  else:
   need(kind==3 and row['name']in('native','rescale'),'G kind/name');need(not any(row[k]for k in ARRAYS),'G exact observation domain');need(row['mul1']==row['fgrants']==0,'G no hidden peer/SFU');need(row['root_writes']==0,'G cannot write Falcon root')
  oracle.g.check(index,row)
  descriptor=0x52393901|(pos<<32)|(epoch<<64)|((unit&65535)<<96)|(bank<<112)|(1<<118)|(1<<119)
  need(row['r_descriptor']==f'{descriptor:032x}','external atomic root true bytes');need((row['r_position'],row['r_unit'],row['r_epoch'],row['r_bank'])==(pos,unit,epoch,bank),'published R metadata persists across other leases')
  need(row['cache_version']==reg_version and row['cache_length']==reg_length and row['cache_owner']==(0x1234 if reg_version else 0),'A registry cross lease/reset exact')
  if kind!=2:need(row['root_writes']==0,'other owner cannot publish R')
  summary.append({k:v for k,v in row.items()if k not in ARRAYS|GARRAYS})
 proto=json.loads((run/'actual.jsonl.protocol.json').read_text())
 if qual:
  need(set(proto)==set('schema accepted declared_epoch_Q_injection_RTL_only cfg_collisions actual_aborts_before_reset actual_stale_before_reset terminal_rejected_edges fabric_high_water root_writes g_aborts_before_second_reset g_stale_before_second_reset g_root_writes checks'.split()),'qualification keys');need(proto['schema']=='shared109-qualification/1'and proto['declared_epoch_Q_injection_RTL_only']is True and proto['checks']==CHECKS,'qualification declarations')
  for k,v in {'accepted':44,'g_aborts_before_second_reset':6,'g_stale_before_second_reset':2,'g_root_writes':3,'cfg_collisions':2,'actual_aborts_before_reset':6,'actual_stale_before_reset':2,'terminal_rejected_edges':24,'fabric_high_water':2,'root_writes':3}.items():need(type(proto[k])is int and proto[k]==v,'qualification actual '+k)
 else:
  need(set(proto)==set('schema accepted leases same_core_no_per_case_reset held_done latched_parameters fabric_high_water external_accepted root_writes g_root_writes aborts stale consumer_lines consumer_releases blocked_acks'.split()),'mixed protocol keys');need(proto['schema']=='shared121-mixed/1','mixed schema')
  for k in ['same_core_no_per_case_reset','held_done','latched_parameters']:need(proto[k]is True,'actual bool '+k)
  for k,v in {'accepted':len(rows),'leases':len(rows),'fabric_high_water':1,'root_writes':2 if m['pilot']else 3,'g_root_writes':2 if m['pilot']else 4,'aborts':0,'stale':0,'external_accepted':sum(r['transactions']for r in rows)}.items():need(type(proto[k])is int and proto[k]==v,'mixed actual '+k)
 return {'G':oracle.g.report(),'rows':summary,'protocol':proto,'all_R_state_codes':sum(len(r['state'])for r in rows),'all_M_A_output_codes':sum(len(r['out'])for r in rows if r['kind']!=2)}

def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 a.out.mkdir(parents=True,exist_ok=False)
 oracle=Oracle(a.input)
 result=inspect(a.input,a.run,oracle)
 rows=[json.loads(x)for x in(a.run/'actual.jsonl').read_text().splitlines()]
 proto=result['protocol']
 need(proto['consumer_lines']==sum(r['result_lines']for r in rows),'every committed beat consumed exactly once')
 need(proto['consumer_releases']==sum(r['result_lines']>0 for r in rows),'each consumer lease explicitly released')
 need(proto['blocked_acks']>0,'early ACK attempts exercised')
 result.update(status='PASS_SHARED121_COMPLETE_INTEGER_COMMITTED_MIXED',receiver_sha256=sha(__file__),run_manifest_sha256=sha(a.run/'manifest.json'))
 upstream.put(a.out/'receipt.json',result)
 print(result['status'])
if __name__=='__main__':main()
