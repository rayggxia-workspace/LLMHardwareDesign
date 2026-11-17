import json,pathlib,statistics,csv,collections,math,hashlib
P=pathlib.Path;root=P(__file__).resolve().parent
inventory=json.loads((root/'inventory.json').read_text());bundle=json.loads((root/'endpoint-binding.json').read_text());binding=bundle['endpoints'];native=bundle.get('native_macro_nets',{})
rows=[];missing=[]
for j in inventory:
 f=root/(j['scheme']+'-'+j['net']+'.summary.json')
 if not f.exists():missing.append(j['scheme']+'/'+j['net']);continue
 r=json.loads(f.read_text())
 if r['exit']!=0:missing.append(j['scheme']+'/'+j['net']);continue
 drivers=[b for b in binding[j['driver']] if b['direction']=='OUTPUT']
 receivers=[b for s in j['sinks'] for b in binding[s] if b['direction']=='INPUT']
 local=[b for b in binding[j['driver']] if b['direction']=='INPUT']
 if j['driver'] in native:local=[b for b in native[j['driver']] if b['direction']=='INPUT']
 caps=[d['model'].get('max_capacitance') for d in drivers]
 limit=caps[0] if len(caps)==1 else None
 remote=sum(b['model'].get('capacitance',0) for b in receivers)
 localcap=sum((b['model'] or {}).get('capacitance',0) for b in local)
 unknown=sum('capacitance' not in (b['model'] or {}) for b in receivers+local)
 load=r['self_fF']+remote+localcap
 row={k:j[k] for k in ['scheme','group','net','driver','length_um','via10','via11']}
 row.update(sinks=';'.join(j['sinks']),driver_cells=';'.join(d['instance']+'/'+d['master']+'/'+d['pin'] for d in drivers),receiver_cells=';'.join(b['instance']+'/'+b['master']+'/'+b['pin'] for b in receivers),driver_count=len(drivers),receiver_pin_count=len(receivers),unknown_pin_caps=unknown,wire_self_fF=r['self_fF'],wire_ground_fF=r['ground_fF'],wire_coupling_fF=r['coupling_signed_fF'],wire_sigma_fF=r['sigma_fF'],relative_sigma=r['relative_sigma'],remote_pin_fF=remote,source_local_pin_fF=localcap,known_total_fF=load,limit_fF=limit,load_limit_ratio=load/limit if limit else None,cap_status=('exceeds' if load>limit else 'not_exceeded_known_load') if limit else 'unresolved',conservation_error_fF=r['conservation_error_fF'],walks=r['walks'],row_sha256=r['raw_sha256'],series_R_estimate_ohm=j['length_um']*.03/2+(j['via10']+j['via11'])*.08,internal_wire_C_included=False,sta_status='not_run_unqualified_CU_or_macro_rewire',existing_sink_driver_terms=';'.join(x for s in j['sinks'] for b in binding[s] for x in b.get('existing_parent_terms',[])))
 row['existing_sink_driver_terms']=';'.join(b['instance']+'/'+b['pin'] for s in j['sinks'] for b in native.get(s,[]) if b['direction']=='OUTPUT')
 row['cap_status_3sigma']=('exceeds' if load-3*r['sigma_fF']>limit else 'below_known_load' if load+3*r['sigma_fF']<limit else 'marginal') if limit else 'unresolved'
 rows.append(row)
fields=list(rows[0]) if rows else []
if fields:
 with (root/'all-nets.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def dist(a):
 a=sorted(a)
 return dict(min=a[0],median=statistics.median(a),p90=a[round(.9*(len(a)-1))],p99=a[round(.99*(len(a)-1))],max=a[-1])
summary=dict(expected=len(inventory),completed=len(rows),missing=missing,groups={},driver_masters=dict(collections.Counter(d['master'] for j in inventory for d in binding[j['driver']] if d['direction']=='OUTPUT')))
for key in sorted(set(r['scheme']+'-'+r['group'] for r in rows)):
 g=[r for r in rows if r['scheme']+'-'+r['group']==key]
 summary['groups'][key]=dict(count=len(g),cap_status=dict(collections.Counter(r['cap_status'] for r in g)),length_um=dist([r['length_um'] for r in g]),wire_self_fF=dist([r['wire_self_fF'] for r in g]),known_total_fF=dist([r['known_total_fF'] for r in g]),R_estimate_ohm=dist([r['series_R_estimate_ohm'] for r in g]),max_relative_sigma=max(r['relative_sigma'] for r in g),max_conservation_error_fF=max(abs(r['conservation_error_fF']) for r in g),largest_load=sorted(g,key=lambda r:r['known_total_fF'],reverse=True)[:5])
summary['quality']=dict(nonpositive_self=sum(r['wire_self_fF']<=0 for r in rows),sigma_over_0_003=sum(r['relative_sigma']>.003 for r in rows),driver_not_unique=sum(r['driver_count']!=1 for r in rows),unknown_pin_caps=sum(r['unknown_pin_caps']>0 for r in rows),no_receiver=sum(r['receiver_pin_count']==0 for r in rows))
summary['cap_status_3sigma']=dict(collections.Counter(r['cap_status_3sigma'] for r in rows))
summary['not_exceeded_known_load']=[r for r in rows if r['cap_status']=='not_exceeded_known_load']
lookup={(r['scheme'],r['net']):r for r in rows};compare=[]
for (s,n),a in lookup.items():
 if s!='A' or ('B',n) not in lookup:continue
 b=lookup['B',n];compare.append(dict(net=n,driver=a['driver'],A_length_um=a['length_um'],B_length_um=b['length_um'],A_wire_fF=a['wire_self_fF'],B_wire_fF=b['wire_self_fF'],delta_fF=b['wire_self_fF']-a['wire_self_fF'],delta_percent=100*(b['wire_self_fF']/a['wire_self_fF']-1)))
if compare:
 with (root/'CU-A-vs-B.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(compare[0]));w.writeheader();w.writerows(compare)
 summary['CU_comparison']=dict(count=len(compare),delta_fF=dist([r['delta_fF'] for r in compare]),delta_percent=dist([r['delta_percent'] for r in compare]))
(root/'all-summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps({k:v for k,v in summary.items() if k not in ['groups','missing','not_exceeded_known_load']},indent=2))
for k,v in summary['groups'].items():print(k,json.dumps({a:b for a,b in v.items() if a!='largest_load'}))
