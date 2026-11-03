"""Probe native fixed-clock DEF overlay without changing the source macro."""
from pathlib import Path
from itertools import zip_longest
from decimal import Decimal
import argparse,hashlib,json,re,subprocess
from native_interchange import tokens,number,lex
p=argparse.ArgumentParser();p.add_argument('--physical',type=Path,required=True);a=p.parse_args()
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
R=a.physical/'flow/results/nangate45/r166_1024/base';odb=R/'6_final.odb';before_sha=sha(odb)
O=Path.cwd()/'clock-route-probe';O.mkdir(exist_ok=False)
def run(name,text):
 script=O/(name+'.tcl');script.write_text(text)
 with(O/(name+'.log')).open('w')as log:subprocess.run(['openroad','-no_init','-exit',str(script)],cwd=O,stdout=log,stderr=subprocess.STDOUT,check=True)
prefix='set_thread_count 16\nread_db {'+str(odb)+'}\n'
run('export',prefix+'''help read_def
set block [ord::get_db_block]
set f [open clock-nets.tsv w]
set clocks 0
foreach net [$block getNets] {
 if {[$net getSigType] eq "CLOCK"} {
  if {[$net getWire] eq "NULL"} {error "Clock net has no source wire"}
  puts $f "[$net getName]\t[$net getWireType]";incr clocks
 }
}
close $f
if {$clocks==0 || [[[$block findBTerm clk] getNet] getSigType] ne "CLOCK"} {error "Clock classification missing"}
set dffs 0
foreach inst [$block getInsts] {
 if {[string match DFF* [[$inst getMaster] getName]]} {
  set ck [$inst findITerm CK]
  if {$ck eq "NULL" || [$ck getNet] eq "NULL" || [[$ck getNet] getSigType] ne "CLOCK"} {error "Unclassified DFF clock"}
  incr dffs
 }
}
puts "R166_FIXED_CLOCK_PROBE_SOURCE; clock_nets=$clocks; dffs=$dffs"
write_def before.def
''')
clocks={line.split('\t')[0]for line in(O/'clock-nets.tsv').read_text().splitlines()};assert clocks
found=set();changed=0;overlay=[];in_nets=False;row=[];headers=[]
with(O/'before.def').open()as stream:
 for line in stream:
  if not in_nets:
   if re.match(r'^\s*(VERSION|DIVIDERCHAR|BUSBITCHARS|DESIGN|UNITS)\b',line):headers.append(line)
   if re.match(r'^\s*NETS\s+\d+\s*;',line):in_nets=True
   continue
  if re.match(r'^\s*END\s+NETS\s*$',line):assert not row;break
  for token in lex.findall(line):
   if token.startswith('#'):continue
   row.append(token)
   if token==';':
    assert row[0]=='-';name=row[1]
    if name in clocks:
     assert name not in found;found.add(name);count=0
     for i in range(1,len(row)):
      if row[i]=='ROUTED'and row[i-1]=='+':row[i]='FIXED';count+=1
     assert count>0,('Source clock wire is not ROUTED',name);changed+=count;overlay.append(' '.join(row)+'\n')
    row=[]
assert found==clocks and len(headers)==5 and not row
(O/'fixed-clocks.def').write_text(''.join(headers)+'NETS '+str(len(clocks))+' ;\n'+''.join(overlay)+'END NETS\nEND DESIGN\n')
#441/442 proved INCREMENTAL does not read the NETS section at all.
# Upstream definReader installs net callbacks for FLOORPLAN; definNet::begin
# replaces the old regular wire. Supply only the same clock NETS and headers.
# Full token comparison below rejects any unintended geometry/connection edit.
run('overlay',prefix+'''read_def -floorplan_initialize {'''+str(O/'fixed-clocks.def')+'''}
write_def after.def
''')
def canonical(path,fix):
 source=iter(tokens(path));nets_seen=False
 for token in source:
  yield token
  if token!='NETS':continue
  assert not nets_seen;nets_seen=True
  yield next(source);semi=next(source);assert semi==';';yield semi
  while True:
   first=next(source)
   if first=='END':
    yield first;end=next(source);assert end=='NETS';yield end;break
   assert first=='-';row=[first]
   while row[-1]!=';':row.append(next(source))
   if row[1]in clocks:
    #443 rebuilt the same clock terminal collection in another order.
    # DEF net connections are unordered. Sort whole connection records,
    # retaining every terminal, record option and duplicate; attributes and
    # all subsequent route tokens remain in their exact original order.
    at=2;connections=[]
    while row[at]=='(':
     end=row.index(')',at)+1;connections.append(tuple(row[at:end]));at=end
    assert row[at]in ['+',';']
    row=row[:2]+[v for connection in sorted(connections)for v in connection]+row[at:]
    if fix:
     for i in range(1,len(row)):
      if row[i]=='ROUTED'and row[i-1]=='+':row[i]='FIXED'
   yield from row
 assert nets_seen
count=0;numeric=0
for x,y in zip_longest(canonical(O/'before.def',True),canonical(O/'after.def',False)):
 assert x is not None and y is not None,('Overlay token count differs',count)
 if x!=y:
  assert number.fullmatch(x)and number.fullmatch(y)and Decimal(x)==Decimal(y),('Overlay changed source geometry/connectivity',count,x,y)
  numeric+=1
 count+=1
assert sha(odb)==before_sha
receipt=dict(passed=True,source_odb=str(odb),source_odb_sha256=before_sha,clock_nets=len(clocks),route_flag_changes=changed,tokens_verified=count,equal_numeric_spellings=numeric,complete_clock_connection_records_sorted=True,artifacts={f.name:dict(sha256=sha(f),bytes=f.stat().st_size)for f in O.iterdir()if f.is_file()},scope='Native targeted floorplan-mode DEF overlay changes only selected clock route flags ROUTED to FIXED. Full source geometry/connectivity/rules token comparison; complete unordered GROUP members and selected clock terminal records sorted without exclusions or deduplication. No source mutation or physical qualification.')
(O/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items()if k!='artifacts'}))
