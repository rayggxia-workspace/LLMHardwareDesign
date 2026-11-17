import pathlib,csv,json,hashlib
p=pathlib.Path(__file__).resolve().parent;rows=list(csv.DictReader((p/'sta-all.csv').open()));assert len(rows)==1292
lookup={(r['key'],int(r['MHz'])):r for r in rows};assert len(lookup)==1292
for key in {r['key'] for r in rows}:
 a=lookup[key,200];b=lookup[key,300]
 assert abs(float(a['setup_ns'])-float(b['setup_ns'])-5/3)<2e-6,key
 assert abs(float(a['hold_ns'])-float(b['hold_ns']))<1e-6,key
 assert a['source_cap_violation']==b['source_cap_violation'] and a['source_slew_violation']==b['source_slew_violation'],key
out=dict(passed=True,cases=1292,route_cases=646,frequency_pair_checks=646,sha256={f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in ['sta-all.csv','sta-summary.json','graphs-rcx.json','node-capacitances.json','node-validation.json','mesh-validation.json','rcx-validation.json','sta-pilot-validation.json','fast-pilot-validation.json']})
(p/'final-validation.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
