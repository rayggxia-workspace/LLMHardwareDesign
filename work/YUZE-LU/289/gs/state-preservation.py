"""Check state element identity and clock/reset/initial-state preservation.
Combine this with the ECO all-state-boundary Boolean correspondence receipt.
"""
import sys,json,re,hashlib
from pathlib import Path
role,arg=sys.argv[1:];c=Path(arg).resolve();out=c/'formal'
root=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-201-compact-ge/2ba89c0bd/source')
sys.path.insert(0,str(root/'project/experiments/block_v1'))
from native_cell_gate import group
lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib').read_text()
top='block_v2_g' if role=='G' else 'local_s_base'
paths=[out/(label+('-physical.json' if role=='G' else '.json')) for label in ('gold','gate')]
modules=[json.loads(p.read_text())['modules'][top] for p in paths]
types={x['type'] for m in modules for x in m['cells'].values()}
sequential={}
for kind in types:
    if kind=='s_sram_256x128_freepdk45':continue
    body=group(lib,'cell',kind)
    if not re.search(r'\b(?:ff|ff_bank|latch|latch_bank)\s*\(',body):continue
    expressions=re.findall(r'\b(?:clocked_on|clocked_on_also|enable|clear|preset)\s*:\s*"([^"]+)"',body)
    pins=set(re.findall(r'\bpin\s*\(\s*"?(\w+)"?\s*\)',body))
    controls=sorted(set(re.findall(r'[A-Za-z_]\w*',' '.join(expressions))) & pins)
    assert controls,(kind,expressions)
    sequential[kind]=controls
def aliases(m):
    a={}
    for n,v in m['netnames'].items():
        for i,b in enumerate(v['bits']):a.setdefault(b,set()).add((n,i))
    for n,v in m['ports'].items():
        for i,b in enumerate(v['bits']):a.setdefault(b,set()).add(('PORT:'+n,i))
    return a
a,b=modules; aa,bb=map(aliases,modules)
states=[{n:x for n,x in m['cells'].items() if x['type'] in sequential} for m in modules]
assert set(states[0])==set(states[1]) and states[0]
checked=[]
for n,x in states[0].items():
    y=states[1][n]
    assert x['type']==y['type'] and x['parameters']==y['parameters'],n
    for pin in sequential[x['type']]:
        before,after=x['connections'][pin],y['connections'][pin]
        assert len(before)==len(after)
        for left,right in zip(before,after):
            if isinstance(left,str) or isinstance(right,str):assert left==right,(n,pin)
            else:assert aa[left] & bb[right],(n,pin,aa[left],bb[right])
    # Preserve any explicit state attributes, including init/reset values.
    state_attrs=lambda attrs:{k:v for k,v in attrs.items() if re.search('init|reset|preset',k,re.I)}
    assert state_attrs(x['attributes'])==state_attrs(y['attributes']),n
    checked.append(dict(instance=n,type=x['type'],controls=sequential[x['type']]))
initial=[]
for name,net in a['netnames'].items():
    if 'init' in net.get('attributes',{}):
        assert name in b['netnames'] and net['attributes']['init']==b['netnames'][name]['attributes'].get('init'),name
        initial.append(name)
assert {n for n,v in b['netnames'].items() if 'init' in v.get('attributes',{})}==set(initial)
report=dict(passed=True,state_count=len(checked),state_cells=checked,explicit_init_nets=initial,
            scope='Exact state instance/type/parameters plus clock/reset/latch-enable identity and explicit initial-state attributes; combined with separate all-state-boundary LEC',
            input_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
(out/'state-preservation.json').write_text(json.dumps(report,indent=2))
