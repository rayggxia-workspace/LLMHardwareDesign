"""Real-view mutation controls for the complete physical interchange receiver."""
from pathlib import Path
from decimal import Decimal
import argparse,json,re,hashlib
from native_interchange import equivalent

p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);a=p.parse_args()
out=Path.cwd()/'interchange-controls';out.mkdir(exist_ok=False)
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
receipt=json.loads((a.source/'INTERCHANGE_RECEIPT.json').read_text());assert receipt['passed']
for name,row in receipt['files'].items():assert sha(a.source/name)==row['sha256']
baseline={name:equivalent(a.source/name,a.source/other)for name,other in receipt['pairs'].items()}
assert baseline==receipt['proof']
controls={}

def reject(name,src,mutate):
 dst=out/(name+src.suffix);changed=False
 with src.open()as reader,dst.open('w')as writer:
  for line in reader:
   if not changed:
    result=mutate(line)
    if result is not None:
     assert result!=line;line=result;changed=True
   writer.write(line)
 assert changed,'No actual source target for '+name
 try:equivalent(src,dst)
 except AssertionError as e:
  controls[name]=dict(passed=True,source_sha256=sha(src),mutant_sha256=sha(dst),rejection=str(e))
 else:raise AssertionError('Real physical mutation accepted: '+name)

def die(line):
 if line.startswith('DIEAREA '):
  return re.sub(r'(\(\s*)([0-9]+)',lambda m:m[1]+str(int(m[2])+1),line,count=1)
reject('die_coordinate',a.source/'bridge.def',die)

state={'group':False}
def group(line):
 if line.startswith('GROUPS '):state['group']=True;return
 if state['group']and re.match(r'^\s*-\s+',line):
  return re.sub(r'^(\s*-\s+\S+\s+)\S+\s+',r'\1',line,count=1)
reject('missing_group_member',a.source/'bridge.def',group)

state={'nets':False}
def connection(line):
 if line.startswith('NETS '):state['nets']=True;return
 if state['nets']and re.search(r'\(\s*\S+\s+\S+\s*\)',line):
  return re.sub(r'(\(\s*)(\S+)(\s+\S+\s*\))',lambda m:m[1]+m[2]+'_FAULT'+m[3],line,count=1)
reject('net_connection',a.source/'bridge.def',connection)

def spacing(line):
 m=re.match(r'^(\s*SPACING\s+)([0-9]+(?:\.[0-9]+)?)(\s*;.*)$',line.rstrip('\n'))
 if m:return m[1]+str(Decimal(m[2])+Decimal('.001'))+m[3]+'\n'
reject('technology_spacing',a.source/'bridge.lef',spacing)

assert len(controls)==4 and all(r['passed']for r in controls.values())
(out/'receipt.json').write_text(json.dumps(dict(passed=True,baseline=baseline,controls=controls,interchange_source=str(a.source),source_receipt_sha256=sha(a.source/'INTERCHANGE_RECEIPT.json'),scope='Exact real-view baseline accepts; changed die coordinate, missing group member, changed net connection and changed technology spacing all reject. No source view or qualification modified.'),indent=2)+'\n')
