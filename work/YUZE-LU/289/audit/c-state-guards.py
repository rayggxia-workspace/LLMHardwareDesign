import json,sys,re,hashlib
from pathlib import Path
out=Path(sys.argv[1]);f=out/'formal';v=out/'explicit-state-v2';top='cfj_group_c_memory_legacy'
sys.path.insert(0,'/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-201-compact-ge/2ba89c0bd/source/project/experiments/block_v1')
from native_cell_gate import group
text=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib').read_text()
def allbits(m):
 return {b for w in list(m['netnames'].values())+list(m['ports'].values()) for b in w['bits'] if isinstance(b,int)}|{b for c in m['cells'].values() for bits in c['connections'].values() for b in bits if isinstance(b,int)}
r={}
for label in ('gold','gate'):
 source=f/(label+'-cut.json');original=json.loads(source.read_text())['modules'][top]
 for typ in {c['type'] for c in original['cells'].values()}:assert not re.search(r'\b(?:ff_bank|latch_bank)\s*\(',group(text,'cell',typ)),typ
 nb={b for w in original['netnames'].values() for b in w['bits'] if isinstance(b,int)};ab=allbits(original)
 assert max(ab)==max(nb)
 actual=v/(label+'.json');changed=json.loads(actual.read_text())['modules'][top]
 if label=='gold':
  extra=[b for n,p in changed['ports'].items() if n.startswith('__extrastate_') for b in p['bits']]
  assert len(extra)==len(set(extra)) and not set(extra)&ab
 r[label]={'source_sha':hashlib.sha256(source.read_bytes()).hexdigest(),'actual_sha':hashlib.sha256(actual.read_bytes()).hexdigest(),'max_all_bits':max(ab),'max_netname_bits':max(nb)}
(v/'independent-structural-guards.json').write_text(json.dumps({'passed':True,'checks':r},indent=2));print('PASS structural guards',out.name)
