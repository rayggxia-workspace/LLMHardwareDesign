"""Static instruction audit. Counts are not measured bandwidth or utilization."""
import json,struct,sys
from collections import Counter,defaultdict
from pathlib import Path
from native_macro_work import measure
from native_mother_dag import actions
from native_stage_schedule import completion_hints
plan=json.loads(Path(sys.argv[1]).read_text());calls=plan['calls'];cost_model=plan['search_plan'].get('cost_model','structural/1')
memory=defaultdict(dict);ddr={};counts=Counter();redundant=[];source_bytes=Counter();source_pages=set();weight_spans=[];group_histogram=Counter();weight_owner=Counter();weight_operator=Counter()
def initial(a):return ('initial',a)
def read_ddr(a):return ddr.get(a,initial(a))
def writes(raw,schema):
 if schema==3 or schema==0x314d5347:return [(struct.unpack_from('<H',raw,20)[0],struct.unpack_from('<H',raw,22)[0])]
 if schema==0x31455052:return [(struct.unpack_from('<H',raw,22)[0],32)]
 if schema==0x31414d52:return [(struct.unpack_from('<H',raw,16)[0],struct.unpack_from('<H',raw,20)[0])]
 if schema==0x3156534e:
  op=struct.unpack_from('<H',raw,6)[0];n=struct.unpack_from('<H',raw,18)[0]
  return [(struct.unpack_from('<H',raw,16 if op==1 else 26)[0],(n+3)//4 if op==1 else 1)]
 if schema==0x31444d45:return [(struct.unpack_from('<H',raw,20)[0],1)]
 if schema==0x32485447:return [(struct.unpack_from('<H',raw,42)[0],struct.unpack_from('<H',raw,40)[0]//16)]
 if schema==0x3152504d:
  return [(struct.unpack_from('<H',raw,120)[0],32),(struct.unpack_from('<H',raw,84)[0],16),(struct.unpack_from('<H',raw,86)[0],raw[74]*2)]
 raise ValueError('missing write-footprint contract '+hex(schema))
for i,c in enumerate(calls):
 raw=bytes.fromhex(c['descriptor_hex']);schema=int.from_bytes(raw[:4],'little');owner=c['group'];words=memory[owner]
 counts[hex(schema)]+=1
 if schema in (0x314c5244,0x31535744):
  word=struct.unpack_from('<H',raw,16)[0];address=struct.unpack_from('<Q',raw,24)[0]
  if schema==0x314c5244:
   tokens=[read_ddr(address+16*j) for j in range(32)]
   if all(words.get(word+j)==v for j,v in enumerate(tokens)):redundant.append({'call':i,'op':'DRL','owner':owner,'address':address,'task':c.get('source_task')})
   for j,v in enumerate(tokens):words[word+j]=v
  else:
   tokens=[words.get(word+j,('unknown',i,j)) for j in range(32)]
   if all(read_ddr(address+16*j)==v for j,v in enumerate(tokens)):redundant.append({'call':i,'op':'DWS','owner':owner,'address':address,'task':c.get('source_task')})
   for j,v in enumerate(tokens):ddr[address+16*j]=v
 else:
  for word,n in writes(raw,schema):
   for j in range(n):words[word+j]=('written',i,word+j)
 if schema==0x3152504d:
  k=struct.unpack_from('<H',raw,76)[0];groups=raw[74];tiles=k//128
  source=struct.unpack_from('<Q',raw,112)[0];head16=bool(raw[83])
  weight_bytes=tiles*groups*(1152 if head16 else 1088)
  source_bytes['weight_record_payload']+=weight_bytes
  weight_owner[owner]+=weight_bytes
  weight_operator[c.get('source_task','unknown').split('::native_range::')[0]]+=weight_bytes
  source_bytes['activation_payload']+=k*4
  source_pages.update(range(source,source+k*4,512))
  base=struct.unpack_from('<Q',raw,48)[0];first=struct.unpack_from('<I',raw,68)[0];stride=struct.unpack_from('<H',raw,72)[0]
  size=1152 if head16 else 1088;group_histogram[groups]+=1
  for group in range(groups):
   begin=base+((first+group*stride)//8)*tiles*size
   weight_spans.append((begin,begin+tiles*size))
unique_weight_bytes=0;end=-1
for first,last in sorted(weight_spans):
 unique_weight_bytes+=max(0,last-max(first,end));end=max(end,last)
durations=[measure({'calls':[dict(c,index=0,after=[])]},cost_model=cost_model)['work_units'] for c in calls]
policy='predicted_first' if plan['search_plan'].get('stage_resources') else 'all'
program,_=actions(calls,wait_policy=policy);t=0;live={};actual_ends={};busy=Counter();wait_counts=Counter();dispatch_slack=Counter()
for a in program:
 if a['op']=='CALL':
  i=a['call_index'];c=calls[i]
  earliest=max((actual_ends[j] for j in c['after']),default=0)
  dispatch_slack[c['group']]+=max(0,t-earliest)
  live[a['target']]=(i,t+durations[i]);actual_ends[i]=t+durations[i];busy[c['group']]+=durations[i]
 else:
  wait_counts['single' if len(a['calls'])==1 else 'joined']+=1
  t=max([t]+[live[target][1] for target in live if a['mask']&(1<<target)])
  for target in list(live):
   if a['mask']&(1<<target):del live[target]
report={'plan_sha256':plan['plan_sha256'],'calls':len(calls),'service_counts':dict(counts),
 'explicit_DRL_bytes':counts['0x314c5244']*512,'explicit_DWS_bytes':counts['0x31535744']*512,
 'MPR_payload_bytes':dict(source_bytes),'MPR_unique_activation_bytes':len(source_pages)*512,
 'MPR_unique_weight_payload_bytes':unique_weight_bytes,
 'MPR_repeated_weight_payload_bytes':source_bytes['weight_record_payload']-unique_weight_bytes,
 'MPR_output_groups_histogram':dict(group_histogram),
 'MPR_weight_payload_by_owner':dict(weight_owner),
 'MPR_largest_operators':weight_operator.most_common(12),
 'proven_redundant_transfers':redundant,'redundant_counts':dict(Counter(x['op'] for x in redundant)),
 'proxy_only':{'cost_model':cost_model,'instruction_schedule_work':t,'DAG_earliest_work':max(completion_hints(calls,cost_model=cost_model),default=0),
  'owner_busy_work':dict(busy),'owner_command_occupancy':{o:v/t for o,v in busy.items()},
  'dispatch_slack_sum_not_critical_path':dict(dispatch_slack),'WAIT_counts':dict(wait_counts)},
 'scope':'symbolic 16B identity/overwrite audit and structural schedule proxy; no physical utilization or throughput claim'}
Path(sys.argv[2]).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='proven_redundant_transfers'}))
