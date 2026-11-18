from pathlib import Path
import ast,re,json,hashlib,pya
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');p=r/'audit/C-v27-native-own-net';p.mkdir(exist_ok=False)
base=r/'audit/C-v27-physical/rcx-material-120031'
parser=r/'audit/C-v27-rcx-normalization-v2/parser-source.py'
d=r/'cu/runs/C-v27-joint-e20-h30/flow/results/nangate45/c-overlay-current/base/6_final.def'
native=r/'audit/C-v27-native-material/receipt.json'
files=[parser,d,native,base/'layers.tsv',base/'vias.tsv']
hashes={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
width={n:int(w) for n,w in (line.split('\t') for line in (base/'layers.tsv').read_text().splitlines())}
vias={};vlayers={}
for line in (base/'vias.tsv').read_text().splitlines():
 n,l,*b=line.split('\t');vias.setdefault(n,[]).append((l,list(map(int,b))))
 if l.startswith('metal'):vlayers.setdefault(n,set()).add(l)
tree=ast.parse(parser.read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='parse')
fmt=lambda pt,e:'( '+str(pt[0])+' '+str(pt[1])+(' '+str(e) if e is not None else '')+' )'
exec(compile(ast.Module(body=[fn],type_ignores=[]),str(parser),'exec'))
text=d.read_text().split('\nNETS ',1)[1].split('\nEND NETS',1)[0]
bodies={m[1]:m[2] for m in re.finditer(r'^\s*-\s+(\S+)\s+(.*?);\s*$',text,re.M|re.S)}
markers=[m for m in json.loads(native.read_text())['markers'] if m['layer'] in ('metal2','metal3')]
assert len(markers)==221
cache={};rows=[]
for m in markers:
 match=re.fullmatch(r'net:(\S+)',m['source']);assert match,m['source'];net=match[1]
 if net not in cache:cache[net]=parse(bodies[net])[0]
 region=cache[net][m['layer']]
 box=pya.Box(*[round(x*2000) for x in m['bbox_um']])
 rows.append(dict(index=m['index'],net=net,layer=m['layer'],bbox_um=m['bbox_um'],same_net_route_fully_covers_marker=(pya.Region(box)-region).is_empty()))
assert hashes=={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
result=dict(accepted=False,scope='Source-net material classification of lower fresh native markers. Parser is frozen explicit DEF widths/extensions/vias. Complete original GDS deck remains independent required gate.',count=len(rows),fully_same_net_route_covered=sum(x['same_net_route_fully_covers_marker'] for x in rows),hashes=hashes,markers=rows)
(p/'receipt.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='markers'},indent=2))
