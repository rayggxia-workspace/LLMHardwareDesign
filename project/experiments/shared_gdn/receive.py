"""Independent file receiver: original97/102 oracles and scalar99 state law."""
import argparse,hashlib,importlib.util,json,struct,copy,shutil
import numpy as np
from gverify import GOracle, GNUMBERS, GSTRINGS, GARRAYS
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
M=module('original_m_reference','project/experiments/v_consumer/reference.py')
A=module('original_a_reference','project/experiments/attention_rtl/receive.py')
R=module('original_r_reference','project/experiments/r_state/reference.py')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(b,m):
 if not b:raise ValueError(m)
def put(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8',newline='\n')
def bound(root):
 m=json.loads((root/'manifest.json').read_text())
 need(type(m['artifacts'])is list and len({e['path']for e in m['artifacts']})==len(m['artifacts']),'artifact unique')
 for e in m['artifacts']:
  p=(root/e['path']).resolve();need(p.is_relative_to(root.resolve()),'artifact path');need(type(e['bytes'])is int and p.stat().st_size==e['bytes']and sha(p)==e['sha256'],'artifact bytes '+e['path'])
 return m
ARRAYS=set('mid A8 delta acc down joined qk score exp sum P out state committed_y'.split())
STRINGS=set('name role sum_hex den_hex r_descriptor'.split())
NUMBERS=set('kind status epoch cycles elapsed compute_cycles export_cycles drain_cycles sreads swrites mul0 mul1 fgrants transactions wire_beats result_lines root_writes cache_owner cache_version cache_length r_position r_unit r_epoch r_bank r_retries'.split())
QUAL_ROLES=['init','initial-A','abort-M-link','recover-M','abort-M-S32','recover-M-S32','same-version-scale','recover-scale','abort-A-store','recover-A-store','abort-A-SFU','recover-A-SFU','abort-A-export','recover-A-export','abort-R-write','old-version-after-R','owner-after-R','recover-registry','reject-R','irreversible-R0','later-M','later-Acached','continued-R1','recover-stale','terminal-max','after-reset-restore','after-reset-A']
GQUAL=['G-restore-native','abort-G-store','G-native0','abort-G-wide','abort-G-link','abort-G-write','reject-G','abort-G-export-link','abort-G-export-result','G-irreversible1','G-bad-version','G-bad-position','G-bad-owner','G-native2-stale','second-reset-Rrestore','G-after-reset-restore']
QUAL_ROLES+=GQUAL
CHECKS=['cfg-write-ACK-collision','cfg-read-response-collision','M-inflight-link-drain','M-inflight-S32-drain','A-accepted-store-ACK-drain','A-inflight-SFU-drain','A-export-drain','R-write-drain-old-root','A-registry-across-M-R-abort','R-candidate-reject','R-irreversible-root-ACK','old-tag-under-current-credit','max-no-wrap-and-late-drain']
CHECKS+=['G-accepted-S-ACK-drain','G-wide-S32-drain','G-link-held-read-drain','G-private-write-effect-once','G-full-candidate-reject','G-D-export-link-drain','G-candidate-result-revoke','G-root-ACK-irrevocable','G-context-position-version-reject','G-old-tag-under-current-credit','G-shared-reset-root-restore']
class Oracle:
 def __init__(self,inp):
  self.newim=bound(inp);need(self.newim['schema']=='shared109-input/1','new input type');self.g=GOracle(inp,self.newim)
  for c in self.newim['copies']:
   if c['target']!='vectors.tsv':need(sha(inp/c['target'])==c['sha256']==sha(c['source']),'new payload exact original')
  old=Path(self.newim['old_input']);need(sha(old/'manifest.json')==self.newim['old_manifest_sha256'],'old binding');inp=old;self.im=bound(inp);need(self.im['schema']=='shared106-input/1'and self.im['status']=='VERIFIED_PAYLOAD_REUSE_NOT_RTL','frozen input type')
  for name,h in self.im['old_manifests'].items():need(sha(Path(name)/'manifest.json')==h,'old input manifest');bound(Path(name))
  for e in self.im['copies']:need(sha(inp/e['target'])==e['sha256']==sha(e['source'])and type(e['bytes'])is int and (inp/e['target']).stat().st_size==e['bytes'],'actual unchanged payload')
  self.rows=json.loads((inp/'cases.json').read_text());self.m={};self.a={};self.aoracle=A.Oracle(Path(self.rows[2]['old_root']))
  for c in self.rows:
   if c['kind']=='M':self.m[c['original']['name']]=M.reference(Path(c['old_root']),c['original'])
   else:self.a[c['original']['name']]=self.aoracle.answer(c['original']['name'])
  self.r=(inp/'r.bin').read_bytes();need(len(self.r)==1048576,'R finite image');self.unit=self.im['selection']['R_unit'];need(self.im['selection']['M']==list(self.m)and self.im['selection']['A']==list(self.a),'selected identities')
 def rstep(self,state,unit,epoch,pos):
  off=0xb0000+pos*2592;h=struct.unpack_from('<IIIIiIiI',self.r,off);need(h[:4]==(0x52393943,pos,0,0)and h[7]==0,'original R coefficient header');x=list(struct.unpack_from('<128i',self.r,off+32));b=list(struct.unpack_from('<256i',self.r,off+544));c=list(struct.unpack_from('<256i',self.r,off+1568));return R.step(state,unit,epoch,x,b,c,h[4],h[5],h[6]),h[5]

def inspect(inp,run,oracle):
 m=bound(run);need(m['status']in('RTL_EXECUTED_NOT_RECEIVED','GATE_EXECUTED_NOT_RECEIVED'),'executed status');need(m['input_manifest_sha256']==sha(inp/'manifest.json'),'input exact')
 bd=json.loads((ROOT/'binding.json').read_text());cmd=json.loads((run/'simulation-command.json').read_text());need(type(cmd['exit'])is int and cmd['exit']==0,'real command exit');argv=cmd['argv'];binary=Path(argv[-5]);build=binary.parent.parent;bm=bound(build);need(binary.name=='Vshared109'and sha(binary)==bm['binary_sha256'],'actual executed binary');need(argv[-4]==str(inp/'vectors.tsv')and argv[-2:]==[str(m['stall']),str(m['pilot'])],'actual input/condition argv')
 for n,h in bd['sources'].items():
  if n.startswith('project/rtl/')or n.endswith('/sim.cpp')or(m['suite']=='qualification'and n.endswith('/qualification.cpp')):need(m['source']['sources'].get(n)==h and bm['source']['sources'].get(n)==h,'exact actual source '+n)
 rows=[json.loads(x)for x in(run/'actual.jsonl').read_text().splitlines()];qual=m['suite']=='qualification';roles=QUAL_ROLES if qual else ['init','G-restore-native','mixed-M0','G-native0','mixed-Afull','mixed-R0']+([]if m['pilot']else['G-native1','mixed-Acached','mixed-M5','mixed-R1','G-native2'])+['G-restore-rescale','G-actual-rescale'];need([x['role']for x in rows]==roles,'exact predeclared order')
 state=[0]*32768;y=[0]*128;unit=oracle.unit;epoch=0;pos=0;bank=0;reg_version=0;reg_length=0;prev_transport=0;summary=[]
 oracle.g.prepare(run,rows)
 for index,row in enumerate(rows):
  need(set(row)==ARRAYS|STRINGS|NUMBERS|GNUMBERS|GSTRINGS|GARRAYS,'exact row keys')
  for k in NUMBERS|GNUMBERS:need(type(row[k])is int and (-(1<<63)if k=='r_unit'else 0)<=row[k]<(1<<64),'typed integer '+k)
  for k in STRINGS|GSTRINGS:need(type(row[k])is str,'typed string '+k)
  for k in ARRAYS|GARRAYS:need(type(row[k])is list and all(type(v)is int for v in row[k]),'integer array '+k)
  role=row['role'];kind=row['kind'];status=row['status'];expected_status=2 if role.startswith('abort-')else 17 if role in('same-version-scale','old-version-after-R','owner-after-R')else 3 if role in('reject-R','reject-G')else 4 if role.startswith('G-bad-')else 0
  need(status==expected_status,'expected status');need(row['wire_beats']==row['transactions']*5,'actual five128bit beats');need(row['result_lines']*(2 if row['kind']==3 else 4)==len(row['g_out']if row['kind']==3 else row['out']),'actual export all words');need(row['cycles']+1==row['elapsed'],'command to held done elapsed');need(row['cycles']>=row['export_cycles']+row['drain_cycles'],'disjoint D phases')
  expected_transport=0xffffffff if role=='terminal-max'else 1 if role in('after-reset-restore','second-reset-Rrestore')else prev_transport+1;need(row['epoch']==expected_transport,'actual no-wrap epoch sequence');prev_transport=expected_transport
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
  for k,v in {'accepted':43,'g_aborts_before_second_reset':6,'g_stale_before_second_reset':1,'g_root_writes':3,'cfg_collisions':2,'actual_aborts_before_reset':6,'actual_stale_before_reset':2,'terminal_rejected_edges':12,'fabric_high_water':2,'root_writes':3}.items():need(type(proto[k])is int and proto[k]==v,'qualification actual '+k)
 else:
  need(set(proto)==set('schema accepted leases same_core_no_per_case_reset held_done latched_parameters fabric_high_water external_accepted root_writes g_root_writes aborts stale'.split()),'mixed protocol keys');need(proto['schema']=='shared109-mixed/1','mixed schema')
  for k in ['same_core_no_per_case_reset','held_done','latched_parameters']:need(proto[k]is True,'actual bool '+k)
  for k,v in {'accepted':len(rows),'leases':len(rows),'fabric_high_water':1,'root_writes':2 if m['pilot']else 3,'g_root_writes':2 if m['pilot']else 4,'aborts':0,'stale':0,'external_accepted':sum(r['transactions']for r in rows)}.items():need(type(proto[k])is int and proto[k]==v,'mixed actual '+k)
 return {'G':oracle.g.report(),'rows':summary,'protocol':proto,'all_R_state_codes':sum(len(r['state'])for r in rows),'all_M_A_output_codes':sum(len(r['out'])for r in rows if r['kind']!=2)}

def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False,parents=True);bd=json.loads((ROOT/'binding.json').read_text())
 for n,h in bd['sources'].items():need(sha(ROOT/n)==h,'receiver source '+n)
 oracle=Oracle(a.input);result=inspect(a.input,a.run,oracle);put(a.out/'receipt.json',{'status':'PASS_FOUR_PROFILE_COMPLETE_INTEGER_AND_PROTOCOL','receiver_source':bd,'run_manifest_sha256':sha(a.run/'manifest.json'),'input_manifest_sha256':sha(a.input/'manifest.json'),**result});print('PASS_FOUR_PROFILE_COMPLETE_INTEGER_AND_PROTOCOL')
if __name__=='__main__':main()
