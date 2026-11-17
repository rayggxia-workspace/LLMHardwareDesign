import json,pathlib,hashlib
p=pathlib.Path(__file__).resolve().parent
index=json.loads((p/'field-probe-index.json').read_text());out=[]
for name,s in index['samples'].items():
 f=pathlib.Path(s['field']).parent/('row-%s.json'%s['master']);r=json.loads(f.read_text());i=r['master'];v=r['values'];total,error=v[i];ground=-r['ground'][0]
 out.append(dict(case=name,net=s['net'],length_um=s['length_um'],self_fF=total,sigma_fF=error,relative_sigma=error/total,ground_fF=ground,coupling_signed_fF=-sum(x[0] for j,x in enumerate(v) if j!=i),conservation_error_fF=sum(x[0] for x in v)+r['ground'][0],walks=r['walks'],row_sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
(p/'probe-summary.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
