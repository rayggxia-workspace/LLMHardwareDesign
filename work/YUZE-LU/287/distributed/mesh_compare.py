import pathlib,json
p=pathlib.Path(__file__).resolve().parent
a=json.loads((p/'edge-pilot-check.json').read_text());b=json.loads((p/'mesh25/edge-pilot-check.json').read_text());rows=[]
for key in a:
 x=a[key]['offsets']['0.125'];y=b[key]['offsets']['0.125'];delta=abs(x['elmore_wire_ns']-y['elmore_wire_ns']*x['total_fF']/y['total_fF'])
 rows.append(dict(net=key,coarse_nodes=a[key]['nodes'],fine_nodes=b[key]['nodes'],normalized_moment_delta_ns=delta,passed=delta<.0002 and y['negative_nodes']==0))
out=dict(passed=all(r['passed'] for r in rows),max_delta_ns=max(r['normalized_moment_delta_ns'] for r in rows),rows=rows)
(p/'mesh-validation.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2));assert out['passed']
