"""Prepare exact actual-route graft, never hypothetical route synthesis.
Usage: generate.py SOURCE_META TARGET_META OUT
Both META directories must be read-only snapshots from snapshot.tcl, bound to frozen source ODBs by caller.
"""
from pathlib import Path
import sys,re,json,hashlib
src,dst,out=map(Path,sys.argv[1:]);assert not out.exists();out.mkdir()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def body(p):
 text=(p/'readback.def').read_text();m=re.search(r'\nNETS\s+\d+\s*;(.*?)\nEND NETS',text,re.S);assert m
 vals=re.findall(r'^\s*-\s+net73798\s+(.*?);\s*$',m[1],re.S|re.M);assert len(vals)==1
 return vals[0]
a,b=body(src),body(dst)
assert re.sub(r'\s+',' ',a.split('+ ROUTED')[0]).strip()==re.sub(r'\s+',' ',b.split('+ ROUTED')[0]).strip()
assert (src/'endpoints.tsv').read_bytes()==(dst/'endpoints.tsv').read_bytes(),'Endpoint master/xy/orientation/actual pin geometry mismatch'
def via(p):
 d={}
 for l in (p/'vias.tsv').read_text().splitlines():
  n,*v=l.split('\t');d.setdefault(n,[]).append(v)
 return {n:sorted(v) for n,v in d.items()}
sv,tv=via(src),via(dst)
sl=dict(l.split('\t') for l in (src/'layers.tsv').read_text().splitlines());tl=dict(l.split('\t') for l in (dst/'layers.tsv').read_text().splitlines())
assert '+ ROUTED' in a
route=a.split('+ ROUTED',1)[1];ops=[];usedvias=set();usedlayers=set()
for branch in re.split(r'\bNEW\s+',route):
 layer,seq=branch.strip().split(None,1);assert re.fullmatch(r'metal\d+',layer) and sl[layer]==tl[layer];usedlayers.add(layer)
 ops.append('$e newPath [$tech findLayer {'+layer+'}] ROUTED');prev=None
 for m in re.finditer(r'\(\s*(\*|-?\d+)\s+(\*|-?\d+)(?:\s+(-?\d+))?\s*\)|(\S+)',seq):
  x,y,ext,n=m.groups()
  if x is not None:
   assert prev is not None or (x!='*' and y!='*')
   pt=(prev[0] if x=='*' else int(x),prev[1] if y=='*' else int(y))
   assert prev is None or pt[0]==prev[0] or pt[1]==prev[1],('Diagonal',prev,pt)
   ops.append('$e addPoint %d %d%s'%(pt[0],pt[1],(' '+ext) if ext is not None else ''));prev=pt
  else:
   assert n in sv and n in tv and sv[n]==tv[n],('Unrecognized or unequal via',n)
   assert re.fullmatch(r'[A-Za-z0-9_]+',n),n;usedvias.add(n)
   ops += ['set v [$b findVia {'+n+'}]','if {$v ne "NULL"} {$e addVia $v} else {set v [$tech findVia {'+n+'}];if {$v eq "NULL"} {error "Via missing"};$e addTechVia $v}']
precheck="""import re,sys
from pathlib import Path
a,b=map(lambda p:Path(p).read_text(),sys.argv[1:])
for sec in ('PINS','SPECIALNETS','COMPONENTS'):
 pattern=r'\\n'+sec+r'\\s+\\d+\\s*;(.*?)\\nEND '+sec
 assert re.search(pattern,a,re.S)[1]==re.search(pattern,b,re.S)[1],sec
pattern=r'^\\s*-\\s+net73798\\s+(.*?);\\s*$'
assert re.findall(pattern,a,re.S|re.M)==re.findall(pattern,b,re.S|re.M),'Target wire differs'
"""
(out/'precheck.py').write_text(precheck)
# All token whitespace must be recognized; unknown encoding fails above rather than silently dropping it.
header=['namespace eval ::i289_clock_graft {','set b [ord::get_db_block]','set tech [[ord::get_db] getTech]','set target [$b findNet net73798]','if {$target eq "NULL" || [$target getSigType] ne "CLOCK"} {error "Clock net missing"}','write_def {'+str(out/'pre-apply.def')+'}','exec python3 {'+str(out/'precheck.py')+'} {'+str(dst/'readback.def')+'} {'+str(out/'pre-apply.def')+'}', 'set w [$target getWire]','if {$w eq "NULL"} {error "Expected previous physical wire"}','odb::dbWire_destroy $w','set w [odb::dbWire_create $target]','set e [odb::new_dbWireEncoder]','$e begin $w']
(out/'hook.tcl').write_text('\n'.join(header+ops+['$e end','odb::delete_dbWireEncoder $e','}'])+'\n')
(out/'source-net.defpart').write_text('- net73798 '+a+';\n');(out/'target-net-before.defpart').write_text('- net73798 '+b+';\n')
json.dump({'prepared':True,'executed':False,'accepted':False,'target':'net73798','used_layers':sorted(usedlayers),'used_vias':sorted(usedvias),'exact_endpoint_master_location_orientation_pin_geometry':True,'via_geometry_exact':True,'layer_width_exact':True,'source_inputs':{str(p):sha(p) for d in (src,dst) for p in d.iterdir() if p.is_file()},'hook_sha256':sha(out/'hook.tcl'),'requirements':'Caller must revalidate frozen ODB metadata hashes before applying only to independent copy; then export full DEF/V. Require every non-target net and all nonNETS sections exact, net73798 material exactly actual source reference, actual wire/endpoint electrical continuity, fresh uncached PG, full material RCX, STA and original GDS checks. Preparation is not acceptance.'},open(str(out/'binding.json'),'w'),indent=2)
