"""Fail-closed LEF/DEF interchange when the native checker uses an older ODB.

The original reader exports the immutable source DB. Technology/cell LEF and
the complete physical/connection DEF must survive the other reader/writer.
Only comments, whitespace, equal numeric spellings and the order of members
within a DEF GROUP may differ. Every member and every group attribute remains.
"""
from pathlib import Path
from itertools import zip_longest
from decimal import Decimal,InvalidOperation
from collections import deque
import hashlib,json,re

sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
lex=re.compile(r'"(?:\\.|[^"\\])*"|#[^\r\n]*|[();]|[^\s();#"]+')
number=re.compile(r'^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$')

def tokens(path):
 in_groups=False;row=[]
 with path.open()as stream:
  for line in stream:
   values=[v for v in lex.findall(line)if not v.startswith('#')]
   if path.suffix=='.def'and re.match(r'^\s*GROUPS\s+\d+\s*;',line):
    assert not in_groups and not row
    in_groups=True
    yield from values
   elif in_groups and re.match(r'^\s*END\s+GROUPS\s*$',line):
    assert not row
    in_groups=False
    yield from values
   elif in_groups:
    for token in values:
     row.append(token)
     if token==';':
      assert len(row)>=3 and row[0]=='-'
      boundary=row.index('+')if'+'in row else len(row)-1
      # Membership is an unordered collection in DEF. Sort the entire
      # collection, retaining duplicates; all following attributes stay exact.
      yield from row[:2]+sorted(row[2:boundary])+row[boundary:]
      row=[]
   else:yield from values
 assert not in_groups and not row

def equivalent(original,reloaded):
 h=hashlib.sha256();context=deque(maxlen=12);count=0;spelling=0
 for a,b in zip_longest(tokens(original),tokens(reloaded)):
  assert a is not None and b is not None,('Interchange token count differs',str(original),count,list(context),a,b)
  value=a
  if a!=b:
   assert number.fullmatch(a)and number.fullmatch(b),('Interchange changed a keyword/name/rule/connection',str(original),count,list(context),a,b)
   assert Decimal(a)==Decimal(b),('Interchange changed a numerical geometry/rule value',str(original),count,list(context),a,b)
   value=str(Decimal(a).normalize());spelling+=1
  h.update(value.encode()+b'\0');context.append(a);count+=1
 assert count>0
 return dict(passed=True,original_sha256=sha(original),reloaded_sha256=sha(reloaded),tokens=count,equal_numeric_spelling_changes=spelling,paired_token_sha256=h.hexdigest(),scope='Complete LEF/DEF token stream identical except comments/whitespace/equal numeric spellings and sorted complete DEF GROUP membership; no member, name, layer, rule, shape, coordinate, connectivity or group attribute exclusion')

def prepare(out,odb,exporter,checker,run):
 original=sha(odb)
 run('bridge-export','set_thread_count 16\nread_db {'+str(odb)+'}\nwrite_lef bridge.lef\nwrite_def bridge.def\n',exporter)
 lefs=sorted(out.glob('bridge*.lef'))
 assert lefs and all(re.fullmatch(r'bridge(?:_[0-9]+)?\.lef',f.name)for f in lefs)
 prefix='set_thread_count 16\n'+''.join('read_lef {'+str(f)+'}\n'for f in lefs)+'read_def {'+str(out/'bridge.def')+'}\n'
 run('bridge-import',prefix+'write_lef bridge-reloaded.lef\nwrite_def bridge-reloaded.def\n',checker)
 pairs={f.name:f.name.replace('bridge','bridge-reloaded',1)for f in lefs}
 pairs['bridge.def']='bridge-reloaded.def'
 assert set(f.name for f in out.glob('bridge-reloaded*.lef'))==set(pairs[f.name]for f in lefs)
 proof={name:equivalent(out/name,out/other)for name,other in pairs.items()}
 assert sha(odb)==original
 files={name:dict(sha256=sha(out/name),bytes=(out/name).stat().st_size)for name in list(pairs)+list(pairs.values())}
 record=dict(passed=True,original_odb_sha256=original,exporter_binary=str(exporter),exporter_binary_sha256=sha(exporter),checker_binary_sha256=sha(checker),files=files,pairs=pairs,proof=proof,scope='Original native reader exports exact source to standard full technology/cell LEF and complete physical/connection DEF. Independent checker roundtrip must preserve all tokens. Source ODB immutable; original extracted STA/PG/full GDS remain separate mandatory gates.')
 (out/'INTERCHANGE_RECEIPT.json').write_text(json.dumps(record,indent=2)+'\n')
 return prefix,record

def receive(source,odb,checker_sha256):
 r=json.loads((source/'INTERCHANGE_RECEIPT.json').read_text())
 assert r['passed']and r['original_odb_sha256']==sha(odb)and r['checker_binary_sha256']==checker_sha256
 assert sha(Path(r['exporter_binary']))==r['exporter_binary_sha256']
 for name,row in r['files'].items():assert sha(source/name)==row['sha256']and(source/name).stat().st_size==row['bytes']
 assert set(r['pairs'])==set(r['proof'])and'bridge.def'in r['pairs']
 for name,other in r['pairs'].items():assert equivalent(source/name,source/other)==r['proof'][name]
 assert sha(source/'before.def')==r['files']['bridge-reloaded.def']['sha256'],'Native checker did not load the verified interchange view'
 return dict(passed=True,receipt_sha256=sha(source/'INTERCHANGE_RECEIPT.json'),source_original_odb_sha256=sha(odb),complete_rules_geometry_connections_roundtrip_verified=True)

if __name__=='__main__':
 import argparse,subprocess,shutil
 p=argparse.ArgumentParser();p.add_argument('--odb',type=Path,required=True);p.add_argument('--checker',type=Path,required=True);a=p.parse_args()
 out=Path.cwd()/'interchange-probe';out.mkdir(exist_ok=False)
 def run(name,tcl,binary):
  script=out/(name+'.tcl');script.write_text(tcl)
  with(out/(name+'.log')).open('w')as log:subprocess.run([str(binary),'-no_init','-exit',str(script)],cwd=out,stdout=log,stderr=subprocess.STDOUT,check=True)
 prepare(out,a.odb,Path(shutil.which('openroad')).resolve(),a.checker,run)
