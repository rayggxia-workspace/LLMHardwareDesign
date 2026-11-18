"""Compare actual overlay ODB G pins with B segment-C inventory; no EDA execution."""
import json,pathlib,sys
p=pathlib.Path(__file__).parent
selected=set((p/'C0.G-outputs.txt').read_text().splitlines()+(p/'C0.G-inputs.txt').read_text().splitlines())
def rows(path,tagged):
 result={}
 for line in path.read_text().splitlines():
  a=line.split('\t')
  if tagged:
   if a[0]!='MACROPIN':continue
   a=a[1:]
  if len(a)!=8 or a[1]!='block_v2_g' or a[2] not in selected:continue
  result.setdefault(a[2],[]).append(dict(instance=a[0],direction=a[3],rect=list(map(int,a[4:]))))
 return {k:sorted(v,key=lambda x:str(x)) for k,v in result.items()}
expected=rows(p/'B-C-pins.tsv',False);actual=rows(pathlib.Path(sys.argv[1]),True)
result=dict(selected_count=len(selected),matched_count=sum(expected.get(k)==actual.get(k) and k in actual for k in selected),differences={k:dict(expected=expected.get(k),actual=actual.get(k)) for k in selected if expected.get(k)!=actual.get(k) or k not in actual})
def geometric(d):
 return {k:[dict(direction=x['direction'],rect=x['rect']) for x in v] for k,v in d.items()}
result['physical_geometry_equal']=geometric(expected)==geometric(actual) and len(actual)==len(selected)
result['instance_mapping']=dict(expected=sorted({x['instance'] for v in expected.values() for x in v}),actual=sorted({x['instance'] for v in actual.values() for x in v}))
result['passed']=not result['differences'] and len(expected)==len(selected)
(p/'G-geometry-comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='differences'},indent=2));sys.exit(0 if result['physical_geometry_equal'] else 1)
