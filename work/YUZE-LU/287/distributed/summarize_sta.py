import pathlib,json,csv,re,collections
P=pathlib.Path;p=P(__file__).resolve().parent;graphs=json.loads((p/'graphs-rcx.json').read_text())
base=P('/public/home/yuzelu/project-circuit/issue287-cu-realwire-20261117')
drivers={'C/'+r['cell']+'/'+r['pin'] for r in csv.DictReader((base/'C-v2/ports.tsv').open(),delimiter='\t') if r['port'].startswith('native_tx_data_o[') and r['pin_direction']=='OUTPUT'};assert len(drivers)==128
rows=[];missing=[];finished=set();locations={};node_caps=json.loads((p/'node-capacitances.json').read_text())
for root,logs in [(p/'sta',list((p/'sta').glob('worker-*.log'))),(p/'sta-fast',list(p.glob('fast-worker-*.log'))),(p/'sta-reverse',list(p.glob('reverse-worker-*.log')))]:
 for log in logs:
  for k,f in re.findall(r'^FINISHED (\S+) (\d+)$',log.read_text(),re.M):finished.add((k,int(f)));locations[k,int(f)]=root/(k+'-'+f)
def electric(path):
 entries=[]
 for line in path.read_text().splitlines():
  a=line.split()
  if len(a)>=5 and a[0] in drivers and '(VIOLATED)' in line:entries.append(dict(pin=a[0],limit=float(a[1]),actual=float(a[2]),slack=float(a[3])))
 return sorted(entries,key=lambda r:r['slack'])
for key,g in graphs.items():
 for mhz in [200,300]:
  if (key,mhz) not in finished:missing.append(key+'-'+str(mhz));continue
  folder=locations[key,mhz];path=folder/'crossing.tsv'
  if not path.exists():missing.append(key+'-'+str(mhz));continue
  cases=list(csv.DictReader(path.open(),delimiter='\t'))
  if len(cases) not in [2,256]:missing.append(key+'-'+str(mhz));continue
  assert all(r['startpoint'].startswith('C/') and r['endpoint'].startswith('U/') for r in cases),(key,mhz)
  assert ({int(r['bit']) for r in cases}==set(range(128)) if len(cases)==256 else {r['bit'] for r in cases}=={'all'}),key
  setup=min((r for r in cases if r['mode']=='max'),key=lambda r:float(r['slack']));hold=min((r for r in cases if r['mode']=='min'),key=lambda r:float(r['slack']))
  cap=electric(folder/'max_capacitance.rpt');slew=electric(folder/'max_slew.rpt')
  row=dict(key=key,scheme=g['scheme'],group=g['group'],net=g['net'],original_driver=g['driver'],original_sinks=';'.join(g['sinks']),length_um=g['length_um'],MHz=mhz,setup_ns=float(setup['slack']),hold_ns=float(hold['slack']),setup_worst_bit=setup['bit'],hold_worst_bit=hold['bit'],startpoint=setup['startpoint'],endpoint=setup['endpoint'],source_cap_violation=bool(cap),source_slew_violation=bool(slew),source_cap_max_fF=cap[0]['actual'] if cap else None,source_slew_max_ns=slew[0]['actual'] if slew else None,wire_C_fF=sum(node_caps[key]),R_ohm=g['rcx_sum_ohm'],report_directory=str(folder),scope='accepted_CU_native_interface_128bit_load_replay_not_actual_AB_system_STA')
  row['passed_this_fixture']=row['setup_ns']>=0 and row['hold_ns']>=0 and not cap and not slew;rows.append(row)
if rows:
 with (p/'sta-all.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
out=dict(expected=1292,completed=len(rows),missing=missing,groups={})
for mhz in [200,300]:
 for group in ['A-CU','B-CU','B-GS']:
  cases=[r for r in rows if r['MHz']==mhz and r['scheme']+'-'+r['group']==group]
  if not cases:continue
  out['groups'][group+'-'+str(mhz)]=dict(count=len(cases),setup_min_ns=min(r['setup_ns'] for r in cases),setup_max_ns=max(r['setup_ns'] for r in cases),setup_negative=sum(r['setup_ns']<0 for r in cases),hold_min_ns=min(r['hold_ns'] for r in cases),cap_violation=sum(r['source_cap_violation'] for r in cases),slew_violation=sum(r['source_slew_violation'] for r in cases),passed=sum(r['passed_this_fixture'] for r in cases))
(p/'sta-summary.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='missing'},indent=2))
