"""Verify campaign hashes, merge observed functional/state coverage and LCOV lines."""
from pathlib import Path
import argparse,hashlib,json,re,sys

TARGETS=['five/U','five/F','five/C','five/P','five/J','recovery/U','recovery/F','recovery/C','recovery/J']
BASE=['baseline','signed','saturating','boundary','length1','length2','length3','length4','continuous','pm_error0','pm_error1','pm_error2','pm_lost0','pm_lost1','pm_lost2','crc_fault']
COMMON_HITS=[0,1,2,3,4,5,6,7,8,9,11,15,16,18,19,20,21,22,23,24,28,32]
HIT_NAMES={0:'reset',1:'all_images_valid',2:'start_accepted',3:'held_host_reply',4:'result_consumed',5:'rejection',6:'pm_readback',7:'crc_verify',8:'native_request',9:'native_response',10:'native_sat_flag',11:'native_error',12:'link_or_output_pending',13:'actual_commit',14:'matching_ack',15:'poison_observed',16:'failed_result',18:'busy_reject',19:'crc_mismatch',20:'fields_reject',21:'target_reject',22:'not_ready',23:'generation_or_sequence_reject',24:'pm_write',25:'J_fragment',26:'J_output_consume',28:'LC_cancel',29:'cohort_drain',30:'cohort_reset',31:'quarantine',32:'unknown_command'}
CONTROL_FOLDERS=('control_rtl_min_v0_1','control_boot_v1','control_native_v1','control_five_boot_v1','control_hetero_boot_v1','control_recovery_boot_v1')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def bits(value):return [i for i in range(value.bit_length()) if value>>i&1]
def integer(v):return int(str(v),0)

def index_check(folder,round_root):
 index=folder/'result.sha256'
 for line in index.read_text().splitlines():
  digest,name=line.split(None,1);p=Path(name)
  p=round_root/p.relative_to('/work') if p.is_absolute() else folder/p
  assert sha(p)==digest,name
 return sha(index)

def line_data(path):
 files={};name=None
 for line in path.read_text().splitlines():
  if line.startswith('SF:'):
   source=line[3:];name='project/'+source.split('/project/',1)[1] if '/project/' in source else None
   if name and (name.split('/')[1] not in CONTROL_FOLDERS or Path(name).name.startswith('tb_')):name=None
   if name:files.setdefault(name,{})
  elif name and line.startswith('DA:'):
   row,count=map(int,line[3:].split(',')[:2]);files[name][row]=files[name].get(row,0)+count
 return files

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 root=a.root;source=root/'r005/source';sys.path.insert(0,str(source/'project/control_rtl_min_v0_1'))
 import network_check
 d=dict(schema='control-matrix-observed-coverage/1',snapshots={},profiles={},core={},software={},source_sha256={},coverage_contract={},missing=[],line_coverage={})
 for rnd in ('r001','r002','r003','r004','r005'):
  r=root/rnd;d['snapshots'][rnd]=dict(source_commit=(r/'source-commit.txt').read_text().strip(),archive_sha256=sha(r/'source.tar'))
 for folder in CONTROL_FOLDERS+('control_task_compiler_v1',):
  for f in (source/'project'/folder).glob('*.sv'):
   name=f.relative_to(source).as_posix()
   assert f.read_bytes()==(root/'r003/source'/name).read_bytes()==(root/'r004/source'/name).read_bytes(),name
 for name in ('compiler.py','audit.py','fixtures.py','reference.py','host.py','generate.py','test_compiler.py'):
  relative='project/control_task_compiler_v1/'+name
  assert sha(source/relative)==sha(root/'r003/source'/relative)==sha(root/'r004/source'/relative),relative
 all_lines={};global_ops=[set(),set()];native_total=0;scenario_bins=[];state_bins=[];seq_bins=[];transition_bins=[];event_bins=[]
 for number,target in enumerate(TARGETS):
  profile=dict(campaigns={},life=[0,0,0],seq=[0,0,0],transitions=[0,0,0],opcodes=[0,0,0],hits=0,supervisor=0,lcov={})
  planned=[c for c in BASE if not(c.startswith('length') and target.startswith('five/') and target!='five/J')]
  expected={('r003','matrix'):{c:6 for c in planned},('r003','legacy'):{'mode-'+str(i):6 for i in range(7 if number<5 else 19)},('r004','matrix'):{'pm_lost'+str(i):2 for i in range(3)},('r005','matrix'):{'max_identity':6}}
  for (rnd,suite),want in expected.items():
   folder=root/rnd/'results'/('variant-%d'%number);digest=index_check(folder,root/rnd);counts={};cases=[]
   for path in sorted((folder/suite).glob('backend-*/*-init-*.log')):
    text=path.read_text();receipts=[l for l in text.splitlines() if l.startswith(('PASS matrix-native','PASS five-boot','PASS recovery kind='))]
    assert len(receipts)==1,path
    case=path.name.split('-init-',1)[0];counts[case]=counts.get(case,0)+1
    assert path.with_suffix('.dat').stat().st_size>0,path
    match=re.findall(r'^COV_BINS hits=([0-9a-f]+) supervisor=([0-9a-f]+)',text,re.M);assert len(match)==1,path
    profile['hits']|=int(match[0][0],16);profile['supervisor']|=int(match[0][1],16)
    states=re.findall(r'^COV_STATE controller=(\d) life=([0-9a-f]+) seq=([0-9a-f]+) transitions=([0-9a-f]+) opcodes=([0-9a-f]+)',text,re.M);assert len(states)==3,path
    for controller,life,seq,trans,op in states:
     k=int(controller)
     for field,value in (('life',life),('seq',seq),('transitions',trans),('opcodes',op)):profile[field][k]|=int(value,16)
    cases.append(dict(path=path.relative_to(folder).as_posix(),sha256=sha(path),coverage_sha256=sha(path.with_suffix('.dat')),receipt=receipts[0]))
   assert counts==want,(target,rnd,suite,counts,want)
   key=rnd+'/'+suite;profile['campaigns'][key]=dict(passed=len(cases),total=len(cases),case_counts=counts,cases=cases,result_index_sha256=digest)
   native_total+=len(cases)
   if rnd!='r004':scenario_bins.extend(target+':'+key+':'+c for c in counts)
   for file in sorted((folder/suite).glob('backend-*/coverage.info')):
    data=line_data(file);profile['lcov'][file.relative_to(folder).as_posix()]=sha(file)
    for name,rows in data.items():
     for row,count in rows.items():all_lines.setdefault(name,{})[row]=all_lines.get(name,{}).get(row,0)+count
  required_hits=COMMON_HITS+([10] if not target.endswith('/J') else [])
  if number>=5:required_hits+=[12,13,14,29,30,31]
  if target.endswith('/J'):required_hits+=[25]
  if target=='five/J':required_hits+=[12,26]
  for hit in required_hits:
   key=target+':event:'+HIT_NAMES[hit];event_bins.append(key)
   if not(profile['hits']>>hit&1):d['missing'].append(key)
  if number>=5 and profile['supervisor']&0x3f!=0x3f:d['missing'].append(target+':supervisor_states:'+hex(profile['supervisor']))
  for k in range(3):
   for state in ([0,1,2,3,4,5,6,8] if k==0 else range(9)):
    key=f'{target}:controller{k}:life{state}';state_bins.append(key)
    if not(profile['life'][k]>>state&1):d['missing'].append(key)
   for state in ([0,1,2,3,4,7,11] if k==0 else [0,1,2,3,4,5,6,7,8,9,11,12]):
    key=f'{target}:controller{k}:seq{state}';seq_bins.append(key)
    if not(profile['seq'][k]>>state&1):d['missing'].append(key)
   for first,last in [(0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(6,5),(8,0)]:
    key=f'{target}:controller{k}:life_transition{first}>{last}';transition_bins.append(key)
    if not(profile['transitions'][k]>>(first*16+last)&1):d['missing'].append(key)
  global_ops[0].update(bits(profile['opcodes'][0]));global_ops[1].update(bits(profile['opcodes'][1]|profile['opcodes'][2]))
  for field in ('life','seq','transitions','opcodes'):profile[field]=[hex(v) for v in profile[field]]
  profile['hits']=hex(profile['hits']);profile['required_events']={str(n):HIT_NAMES[n] for n in required_hits};d['profiles'][target]=profile
 core_total=0;mutations=0
 for suite,file in [('compact','report.json'),('mother','mother_report.json'),('cancel','report.json'),('fault','report.json'),('network','network_report.json'),('object','report.json'),('transfer','report.json')]:
  folder=root/'r003/core'/suite;path=folder/file;report=json.loads(path.read_text());rows=report.get('results',report.get('cases'));assert isinstance(rows,(list,dict))
  count=len(rows);m=len(report.get('mutation_checks',[]));core_total+=count;mutations+=m
  d['core'][suite]=dict(passed=count,total=count,observer_mutations_rejected=m,report_sha256=sha(path),trace_sha256={x.relative_to(folder).as_posix():sha(x) for x in sorted(folder.rglob('*.log')) if not 'obj_dir' in x.parts})
 for path in sorted((root/'r003/core/compact').glob('*/trace.log')):
  trace=network_check.decode(path.read_text())
  for role,rows in [(0,trace['mother'])]+[(1,x['cycles']) for x in trace['locals']]:
   for row in rows:
    s=row['signals']
    if integer(s.get('trace_retire_o',0)):global_ops[role].add(integer(s.get('trace_opcode_o',0)))
 desired=[{0x10,0x11,0x12,0x13,0x15,0x1f},{0x40,0x41,0x42,0x43,0x44,0x45,0x49,0x4a,0x4b,0x4f}]
 for role in (0,1):
  for op in sorted(desired[role]-global_ops[role]):d['missing'].append(f'global_opcode_role{role}:{op:#x}')
 d['opcode_coverage']=dict(required=[sorted(x) for x in desired],observed=[sorted(x) for x in global_ops],scope='native EXEC subset plus actual compact generic-controller fixture; not every opcode on every native target')
 for suite in ('compiler','matrix'):
  path=root/'r005/software'/(suite+'.json');data=json.loads(path.read_text());assert data['passed']==data['total']
  d['software'][suite]=dict(passed=data['passed'],total=data['total'],sha256=sha(path))
 for name,rows in sorted(all_lines.items()):d['line_coverage'][name]=dict(hit=sum(c>0 for c in rows.values()),total=len(rows),unhit_lines=[r for r,c in sorted(rows.items()) if c==0])
 d['coverage_contract']=dict(scenario_crosses=len(scenario_bins),lifecycle_states=len(state_bins),native_sequencer_states=len(seq_bins),normal_reset_transitions=len(transition_bins),host_native_events=len(event_bins),global_opcodes=16,supervisor_states=24,
    exclusions=['Five same-type targets have no directed SEND/RESERVE/RECEIVE link; length crosses apply only to J or directed topology.','J clamp data is checked, but the native J done interface does not export a saturation flag; SAT diagnostic is not claimed.','MC sequencer BIND states and LC REPORT state are covered by the generic compact fixture, outside the compiled native recipe.','Line coverage is union of Verilator LCOV DA records for selected control sources only; not branch/toggle/instance-product or physical coverage.'])
 d['summary']=dict(native_passed=native_total,native_total=native_total,core_passed=core_total,core_total=core_total,rtl_total=native_total+core_total,observer_mutations_rejected=mutations,
    software_passed=sum(v['passed'] for v in d['software'].values()),line_hit=sum(v['hit'] for v in d['line_coverage'].values()),line_total=sum(v['total'] for v in d['line_coverage'].values()),missing_required_bins=len(d['missing']))
 for folder in CONTROL_FOLDERS+('control_task_compiler_v1','control_matrix_v1'):
  for path in sorted((source/'project'/folder).glob('*')):
   if path.is_file() and path.suffix in ('.sv','.svh','.py','.sh','.json'):d['source_sha256'][path.relative_to(source).as_posix()]=sha(path)
 d['aggregate_sha256']=sha(Path(__file__))
 a.out.write_text(json.dumps(d,indent=2)+'\n')
 print(json.dumps(dict(summary=d['summary'],contract=d['coverage_contract'],missing=d['missing'],sha256=sha(a.out))))
if __name__=='__main__':main()
