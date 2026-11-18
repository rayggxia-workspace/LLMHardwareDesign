"""Pure read-only JSON/LEF audit after zero-bloat abstract generation."""
import sys,json,hashlib
from pathlib import Path
from compare_lef import parse,subtract
candidate=Path(sys.argv[1]);name=sys.argv[2];folder=candidate/'parent-abstract-v3'
raw=folder/(name+'-raw.lef');final=folder/(name+'.lef');a,b=map(parse,[raw,final]);errors=[]
for layer,rects in a['obs'].items():
 for r in rects:
  pieces=[r]
  for q in b['obs'].get(layer,[]):
   pieces=[z for x in pieces for z in subtract(x,q)]
   if not pieces:break
  if pieces:errors.append(dict(layer=layer,uncovered=pieces[:3]))
upper_exact={k:sorted(a['obs'].get(k,[]))==sorted(b['obs'].get(k,[])) for k in ['metal7','metal8','metal9','metal10']}
tcl=(folder/'export.tcl').read_text();receipt=json.loads((folder/'receipt.json').read_text())
checks=dict(zero_bloat='write_abstract_lef -bloat_factor 0 ' in tcl,size_exact=a['size']==b['size'],pins_exact=a['pins']==b['pins'],term_direction_exact={k:v[0] for k,v in a['terms'].items()}=={k:v[0] for k,v in b['terms'].items()},raw_obstructions_fully_covered=not errors,upper_metal_exact=all(upper_exact.values()),source_receipt_passed=receipt['passed'])
result=dict(passed=all(checks.values()),checks=checks,upper_exact=upper_exact,errors=errors[:20],cut_obs_counts={k:len(v) for k,v in b['obs'].items() if k.startswith('via')},input_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [raw,final,folder/'export.tcl',folder/'receipt.json']},scope='No raw ODB-export obstruction removed; upper M7-M10 exact; lower union conservative. GDS cut extraction source/hash and merged native DRC remain separate mandatory evidence.')
Path(sys.argv[3]).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));assert result['passed']
