"""Independent server-only bigint/full-K receiver; imports no producer or RTL driver."""
import argparse,copy,hashlib,json,math,re
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(v,s):
 if not v:raise ValueError(s)
def load(p):return json.loads(Path(p).read_text())
def rne(n,s):
 need(s>=0,'negative shift');q,r=divmod(abs(n),1<<s);q+=2*r>(1<<s)or(2*r==(1<<s)and q%2==1);return -q if n<0 else q
def ints(raw):return [int.from_bytes(raw[i:i+4],'little',signed=True)for i in range(0,len(raw),4)]
def norm(x,g,eps):
 need(len(x)==len(g)and len(x)in(1536,2560),'supported independent H');s=sum(v*v for v in x);d=math.isqrt((s//len(x)+eps)<<40)
 if not d:return 2,[],s,d
 out=[]
 for v,w in zip(x,g):
  n=v*w*4096;q,rem=divmod(abs(n),d);q+=2*rem>d or(2*rem==d and q%2==1);q=-q if n<0 else q
  if not -(1<<31)<=q<(1<<31):return 3,[],s,d
  out.append(q)
 return 0,out,s,d

def matrix_reference(root,c,cache):
 original=c['source_case'];raw=(root/original['payload1'if cache else'payload0']).read_bytes()
 if cache:
  a=np.frombuffer(raw[:4096],np.int8).reshape(8,512).astype(np.int32);v=np.frombuffer(raw[4096:],np.uint8).reshape(1536,8,33,16);head=v[:,:,0];w=v[:,:,1:].copy().view(np.int8).reshape(1536,8,512).astype(np.int32);acc=(a*w).sum(axis=2,dtype=np.int64)
 else:
  v=np.frombuffer(raw,np.uint8).reshape(1536,8,65,16);body=v[:,:,1:];head=v[:,:,0];acc=(body[:,:,:,:8].view(np.int8).astype(np.int32)*body[:,:,:,8:].view(np.int8).astype(np.int32)).sum(axis=(2,3),dtype=np.int64)
 down=[];joined=[]
 for row in range(1536):
  total=0
  for rank in range(8):
   h=head[row,rank].tobytes();mant=int.from_bytes(h[:4],'little',signed=True);shift=31-int.from_bytes(h[4:6],'little',signed=True)-int.from_bytes(h[6:8],'little',signed=True);gate=int.from_bytes(h[8:10],'little');y=rne(int(acc[row,rank])*mant,shift);need(-(1<<31)<=y<(1<<31),'down I32');down.append(y);total+=y*gate
  h=head[row,0].tobytes();res=int.from_bytes(h[10:14],'little',signed=True);joined.append(rne(rne(total,15)*c['coefficient'],20)+res)
 old=load(root/original['original']);need(acc.reshape(-1).tolist()==sum(old['acc'],[])and down==sum(old['down'],[])and joined==old['joined'],'original completeM source')
 g=ints(bytes.fromhex(c['gamma']));st,y,s,d=norm(joined,g,c['epsilon']);need(st==0 and y==old['norm'],'prior norm numerical continuity')
 return {'x':joined,'acc':acc.reshape(-1).tolist(),'down':down,'joined':joined,'gamma':g}

ARRAYS={'acc','down','joined','out','sum_words','den_words','gamma_addresses','gamma_words','external_gamma_addresses','m_counter_before','m_counter_after'}
SCALARS={'kind','h','cache','gamma_stream','gamma_fault','epoch','status','cycles','active_edges','norm_cycles','reads','writes','M_packets','M_MACs','M_store_lines','wire_beats','transactions','cache_reads','cache_writes','mul_grants0','mul_grants1','gamma_loads','gamma_stores','den_events','port_wait_m','port_wait_n','setup_edges','command_edges','completion_edges','result_edges','total_edges','guard_setup_edges','guard_result_edges'}

def check(row,c,ref):
 need(type(row)is dict and set(row)==SCALARS|ARRAYS|{'name','role'},'exact typed row schema')
 need(all(type(row[k])is int and row[k]>=0 for k in SCALARS),'integer scalar fields, not bool/string')
 need(all(type(row[k])is list and all(type(v)is int for v in row[k])for k in ARRAYS),'typed integer arrays')
 need(row['name']==c['name']and row['kind']==int(c['kind']=='norm')and row['h']==c['h']and row['cache']in(0,1)and row['gamma_stream']in(0,1),'case shape/mode binding')
 stream=row['gamma_stream'];h=c['h'];n=h//4;g=ref['gamma'];negative=row['role'].startswith('negative-')
 need(row['gamma_fault']==({'negative-shifted-gamma':1,'negative-stale-gamma':2}.get(row['role'],0)),'fault only explicit rejected numerical runs')
 actual_g=g[256:]+g[:256]if row['gamma_fault']==1 else(g[:256]*(h//256)if row['gamma_fault']==2 else g)
 status,y,s,d=norm(ref['x'],actual_g,c['epsilon']);need(row['status']==status and row['out']==y,'independent full row integer output')
 if negative:
  st0,y0,_,_=norm(ref['x'],g,c['epsilon']);need(status==0 and st0==0 and y!=y0,'actual corrupted transport must be detected against correct reference')
 need(row['acc']==ref.get('acc',[])and row['down']==ref.get('down',[])and row['joined']==ref.get('joined',[]),'actual fullM intermediate consumers')
 need(len(row['sum_words'])==len(row['den_words'])==4 and all(0<=v<(1<<32)for v in row['sum_words']+row['den_words']),'U128 telemetry words')
 need(sum(v<<(32*i)for i,v in enumerate(row['sum_words']))==s and sum(v<<(32*i)for i,v in enumerate(row['den_words']))==d and row['den_events']==1,'one entireH sum/den')
 expect_g=actual_g if stream and status==0 else[];need(row['gamma_words']==expect_g,'actual staged gamma values')
 need(row['gamma_addresses']==([n+i%64 for i in range(n)]if expect_g else[]),'actual tile mapping/old slot prevention')
 need(row['external_gamma_addresses']==([0x01000000+16*i for i in range(n)]if expect_g else[]),'actual gamma request sequence')
 packet=0 if c['kind']=='norm'else(405760 if row['cache']else 798720)
 need(len(row['m_counter_before'])==len(row['m_counter_after'])==5,'raw M counters shape')
 if c['kind']=='norm':need(row['m_counter_before']==row['m_counter_after'],'no hidden M operations or stale counter attribution')
 else:need(row['m_counter_after']==[row[k]for k in('M_packets','M_MACs','M_store_lines','cache_reads','cache_writes')],'raw M outputs equal transaction counts')
 need(row['M_packets']==packet and row['M_MACs']==(0 if c['kind']=='norm'else 6291456)and row['M_store_lines']==(0 if c['kind']=='norm'else 384),'complete M scope')
 need(row['reads']==(3*n if status==0 else n)and row['writes']==((1+stream)*n if status==0 else 0),'all finite S norm operations')
 need(row['gamma_loads']==row['gamma_stores']==(n if expect_g else 0),'actual finite gamma DMA')
 need(row['transactions']==packet+row['gamma_loads']and row['wire_beats']==5*row['transactions'],'external fivebeat packet accounting')
 need(row['cache_reads']==(393216 if c['kind']=='chain'and row['cache']else 0)and row['cache_writes']==(256 if c['kind']=='chain'and row['cache']else 0),'shared A capacity')
 need(row['mul_grants0']==(26112 if c['kind']=='chain'else 0)and row['mul_grants1']==(2*h if status==0 else h),'shared S32 full arithmetic')
 need(row['setup_edges']==2*((n if c['kind']=='norm'else 0)+(n if not stream else 0))and row['result_edges']==(2*n if status==0 else 0),'real caller source/result scope')
 need(row['cycles']==row['active_edges']and row['completion_edges']==5,'whole active/completion edges')
 need(row['command_edges']==(6 if row['role']=='restart-stage-20'else 1),'all parameter acceptance/cfg competition edges')
 need(row['total_edges']==row['setup_edges']+row['command_edges']+row['active_edges']+row['completion_edges']+row['result_edges'],'fair total measured scope')
 guard=768-(n+64)+256 if c['kind']=='norm'else(320*stream+256*(1-row['cache']))
 need(row['guard_setup_edges']==2*guard and row['guard_result_edges']==2*(guard+(256 if c['kind']=='chain'and row['cache']else 0)),'separate canary instrumentation cost')
 return {'status':'REJECTED_BAD_TRANSPORT'if negative else('PASS_EXPECTED_ZERO_DEN'if status else'PASS_BIT_EXACT'),'gamma_elements':len(expect_g)}

def protocol(p,rows):
 expected={'schema':'gamma93-protocol-v1','commands_accepted':67,'abort_stages':9,'invalid_commands':5,'blocked_command_edges':3,'held_done_edges':224,'parameter_mutations':67,'mode_transitions':3,'soft_aborts_before_reset':10,'stale_before_reset':1,'control_reset_conflicts':4,'terminal_rejected_edges':5,'negative_RTL_runs':2,'sum_barrier_checks':sum(r['writes']for r in rows)+193,'canary_line_checks':sum(r['guard_result_edges']//2 for r in rows),'fabric_response_high_water':2,'records_written':51}
 need(type(p)is dict and set(p)==set(expected)|{'parameter_toggle_edges'},'exact protocol required fields')
 need(type(p['parameter_toggle_edges'])is int and p['parameter_toggle_edges']>=sum(r['active_edges']for r in rows),'actual every-busy-edge parameter mutation')
 for k,v in expected.items():need(type(p[k])is type(v)and p[k]==v,'measured protocol '+k)

def bridge_contract():
 source=ROOT/'project/rtl/wide_service/memory_link.sv';s=source.read_text();m=re.search(r'output wire \[(\d+):0\] wire_data',s);need(m is not None,'actual bridge serialized-data declaration');bits=int(m.group(1))+1
 need(bits==128 and 'state==1||state==2||state==3||state==6||state==7||state==8' in s and 'state<=sr_wr?3:4' in s and 'if(ep_wr)begin dout<=0;state<=9;end else state<=8' in s,'known read five-beat state graph')
 return {'source_sha256':sha(source),'wire_bits_per_beat':bits,'read_header_beats':4,'read_payload_beats':1,'read_wire_bytes':5*bits//8,'read_payload_bytes':bits//8,'epoch_sideband_bits':32,'epoch_serialized_in_fivebeat':False,'cfg_header_protocol':'not modeled; cfg128 data and request/response edges reported separately'}

def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();need(not a.out.exists(),'new receiver output');bd=load(ROOT/'binding.json')
 for n,h in bd['sources'].items():need(sha(ROOT/n)==h,'receiver source SHA')
 im=load(a.input/'manifest.json');rm=load(a.run/'manifest.json');need(rm['schema']=='gamma93-run-v1'and rm['status']=='RTL_EXECUTED_NOT_RECEIVED'and rm['baseline']is False and type(rm['stall'])is int and rm['stall']in(0,1),'actual run qualification')
 need(rm['task']=='sim'and rm['source']['commit']and im['source']['commit'],'actual simulation/source provenance')
 for n,h in bd['sources'].items():
  if n.startswith('project/rtl/')or n.endswith('/chain_sim.cpp'):need(rm['source']['sources'].get(n)==h,'receiver exact run source '+n)
 need(im['source']['sources'].get('project/experiments/gamma_stream/inputs.py')==bd['sources']['project/experiments/gamma_stream/inputs.py'],'input producer source binding')
 need(rm['input_manifest_sha256']==sha(a.input/'manifest.json')and im['schema']=='gamma93-input-v1'and im['status']=='PASS_VERIFIED_INPUTS_NOT_RTL','input protocol binding')
 for root,mf in((a.input,im),(a.run,rm)):
  need(type(mf['artifacts'])is list and len({e['path']for e in mf['artifacts']})==len(mf['artifacts']),'unique artifact paths')
  for e in mf['artifacts']:
   need(set(e)=={'path','bytes','sha256'}and type(e['bytes'])is int and e['bytes']>=0 and Path(e['path']).name==e['path'],'typed root-only artifact schema')
   need(sha(root/e['path'])==e['sha256']and(root/e['path']).stat().st_size==e['bytes'],'actual input/run bytes')
 old=Path(im['old_root']);need(str(old)=='/public/home/yuzelu/RuizhiLiang/issue84-cache-share-20261025/input01'and sha(old/'manifest.json')==im['old_manifest_sha256'],'explicit old input root/SHA')
 for e in load(old/'manifest.json')['artifacts']:need(sha(old/e['path'])==e['sha256'],'every original physical input')
 cases=load(a.input/'cases.json');lookup={c['name']:c for c in cases};need(len(cases)==12 and len(lookup)==12,'exact source cohort')
 refs={}
 for c in cases:
  for cache in(0,1):refs[c['name'],cache]=matrix_reference(old,c,cache)if c['kind']=='chain'else{'x':ints(bytes.fromhex(c['x'])),'gamma':ints(bytes.fromhex(c['gamma']))}
 bridge=bridge_contract()
 rows=[json.loads(s)for s in(a.run/'actual.jsonl').read_text().splitlines()];need(len(rows)==51,'all primary/recovery/negative commands')
 seen=set();summary=[];primary=set();negative_count=0
 for row in rows:
  need(row.get('name')in lookup and type(row.get('cache'))is int and row['cache']in(0,1),'row source/mode')
  c=lookup[row['name']];identity=(row['name'],row['cache'],row.get('gamma_stream'),row.get('role'));need(identity not in seen,'no duplicate records');seen.add(identity)
  res=check(row,c,refs[row['name'],row['cache']]);negative_count+=res['status']=='REJECTED_BAD_TRANSPORT'
  if row['role']=='primary':primary.add((row['name'],row['cache'],row['gamma_stream']))
  summary.append({**{k:v for k,v in row.items()if k not in ARRAYS},'verdict':res['status'],'external_wire_bytes':row['wire_beats']*bridge['wire_bits_per_beat']//8,'external_response_payload_bytes':row['transactions']*bridge['read_payload_bytes']})
 expected={(c['name'],cache,g)for c in cases for cache in((0,1)if c['kind']=='chain'else(1,))for g in((0,1)if c['kind']=='chain'else(1,))};need(primary==expected and negative_count==2,'complete primary grid and corrupted transport exclusions')
 roles={'primary','mixed-return-fullM','mixed-return-norm','restart-stale-gamma','restart-hard-reset','last-legal-epoch','negative-shifted-gamma','negative-stale-gamma'}|{'restart-stage-'+str(s)for s in(4,8,20,21,22,23,11,15,17)}|{'restart-error-'+str(s)for s in range(5)};need({r['role']for r in rows}==roles,'all required recovery modes')
 proto=load(a.run/'actual.jsonl.protocol.json');protocol(proto,rows)
 quality=[]
 for c in cases:
  if 'native'not in c:continue
  native=load(a.input/c['native']);ref=refs[c['name'],1];_,y,_,_=norm(ref['x'],ref['gamma'],17);actual=np.asarray(y,dtype=np.float64)/4096;fp=np.asarray(native['captured_native'],dtype=np.float64);err=actual-fp
  quality.append({'name':c['name'],'integer_vs_captured_FP32_relative_l2':float(np.linalg.norm(err)/max(np.linalg.norm(fp),1e-30)),'integer_vs_captured_FP32_max_abs':float(np.max(np.abs(err))),'gamma_encoding':'effective 1+raw -> I32Q20','x_encoding':'I32Q12','note':'selected norm rows only; no wholemodel accuracy or BF16 exact reproduction claim'})
 negatives=[]
 for name,edit in [('output',lambda r:r['out'].__setitem__(0,r['out'][0]^1)),('global_den',lambda r:r['den_words'].__setitem__(0,r['den_words'][0]^1)),('missing_field',lambda r:r.pop('sum_words')),('boolean_count',lambda r:r.update(gamma_loads=True))]:
  bad=copy.deepcopy(rows[0]);edit(bad)
  try:check(bad,lookup[bad['name']],refs[bad['name'],bad['cache']])
  except ValueError:negatives.append(name)
  else:raise ValueError('corrupted row accepted '+name)
 for bad in [dict(proto,records_written=48),dict(proto,negative_RTL_runs=True),{k:v for k,v in proto.items()if k!='stale_before_reset'},dict(proto,extra=1)]:
  try:protocol(bad,rows)
  except ValueError:pass
  else:raise ValueError('protocol corruption accepted')
 result={'schema':'gamma93-receipt-v1','status':'PASS_GAMMA_INTEGER_AND_PROTOCOL','source':bd,'run_source':rm['source'],'input_manifest_sha256':sha(a.input/'manifest.json'),'run_manifest_sha256':sha(a.run/'manifest.json'),'stall':rm['stall'],'records':51,'bit_exact_success_outputs':48,'expected_zero_den_records':1,'actual_bad_transport_runs_rejected':2,'protocol':proto,'bridge_contract':bridge,'rows':summary,'gemma_quality':quality,'receiver_negative_cases':negatives,'protocol_negative_cases':4}
 a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(result['status']);print(json.dumps(quality))
if __name__=='__main__':main()
