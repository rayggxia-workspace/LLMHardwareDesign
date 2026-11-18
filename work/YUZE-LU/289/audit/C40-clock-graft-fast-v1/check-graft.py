import pya,re,json,ast,hashlib
from pathlib import Path
p=Path('.');source=(p/'source-meta/readback.def').read_text();before=(p/'target-meta/readback.def').read_text();after=(p/'results/6_final.def').read_text()
def section(t,n):return re.search(r'\n'+n+r'\s+\d+\s*;(.*?)\nEND '+n,t,re.S)[1]
for name in ('PINS','SPECIALNETS','COMPONENTS'):assert section(before,name)==section(after,name),name
pat=re.compile(r'^\s*-\s+(\S+)\s+(.*?);\s*$',re.M|re.S)
def nets(t):return {m[1]:m[2] for m in pat.finditer(section(t,'NETS'))}
a,b,ref=nets(before),nets(after),nets(source);assert a.keys()==b.keys();changed=[n for n in a if a[n]!=b[n]];assert changed==['net73798'],changed
width=dict((n,int(w)) for n,w in (l.split('\t') for l in (p/'source-meta/layers.tsv').read_text().splitlines()));vias={};vlayers={}
for l in (p/'source-meta/vias.tsv').read_text().splitlines():
 n,layer,*box=l.split('\t');vias.setdefault(n,[]).append((layer,list(map(int,box))))
 if layer.startswith('metal'):vlayers.setdefault(n,set()).add(layer)
fmt=lambda point,e:'( '+str(point[0])+' '+str(point[1])+(' '+str(e) if e is not None else '')+' )'
tree=ast.parse((p/'def-material.py').read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='parse');exec(compile(ast.Module(body=[fn],type_ignores=[]),'strict-parser','exec'),globals())
x,_=parse(b['net73798']);y,_=parse(ref['net73798']);assert x.keys()==y.keys() and all((x[l]^y[l]).is_empty() for l in x)
files=[p/'source-meta/readback.def',p/'target-meta/readback.def',p/'results/6_final.def',p/'generated/hook.tcl',p/'generated/binding.json',p/'apply-before.v',p/'results/6_final.v']
json.dump({'passed':True,'accepted':False,'only_changed_wire':'net73798','all_other_net_bodies_exact':True,'nets_checked':len(a),'components_pins_specialnets_exact':True,'actual_reference_clock_material_exact_all_layers':True,'logic_bytes_exact':(p/'apply-before.v').read_bytes()==(p/'results/6_final.v').read_bytes(),'source_hashes':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}},open('structural-receipt.json','w'),indent=2)
