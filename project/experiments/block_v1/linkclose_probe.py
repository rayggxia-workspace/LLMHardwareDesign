"""Read-only physical prerequisites for representative interconnect closure.

Runs only inside an allocated EDA worker. No accepted database is rewritten.
"""
import hashlib
import json
from pathlib import Path


def legacy_python_probe(root, out, cpus, run):
    assert cpus == 16
    config = root / 'project/experiments/block_v1/interconnect-sources.json'
    native = json.loads(config.read_text())['macros']
    for kind, row in native.items():
        path = Path(row['verilog']).with_suffix('.odb')
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row['hashes']['6_final.odb']
    script = '''import odb,json
from pathlib import Path
config=json.loads(Path(CONFIG).read_text())['macros']
result={}
for kind,row in config.items():
 db=odb.dbDatabase.create();odb.read_db(db,str(Path(row['verilog']).with_suffix('.odb')))
 block=db.getChip().getBlock();tech=db.getTech()
 pins=[]
 for term in block.getBTerms():
  if term.getSigType() in ('POWER','GROUND'):continue
  boxes=[dict(layer=b.getTechLayer().getName(),box=[b.xMin(),b.yMin(),b.xMax(),b.yMax()]) for p in term.getBPins() for b in p.getBoxes()]
  net=term.getNet();drivers=[];loads=[]
  for it in net.getITerms():
   mt=it.getMTerm()
   if mt.getSigType() in ('POWER','GROUND'):continue
   bbox=it.getBBox()
   entry=dict(inst=it.getInst().getName(),pin=mt.getName(),master=it.getInst().getMaster().getName(),bbox=list(bbox[1:]) if isinstance(bbox,tuple) else str(bbox))
   (drivers if mt.getIoType()=='OUTPUT' else loads).append(entry)
  pins.append(dict(name=term.getName(),direction=term.getIoType(),boxes=boxes,drivers=drivers,loads=loads))
 rows=[dict(name=r.getName(),origin=list(r.getOrigin()),orientation=str(r.getOrient()),count=r.getSiteCount(),spacing=r.getSpacing(),site=r.getSite().getName(),width=r.getSite().getWidth(),height=r.getSite().getHeight()) for r in block.getRows()]
 masters={name:dict(width=db.findMaster(name).getWidth(),height=db.findMaster(name).getHeight(),terms=[(t.getName(),t.getSigType(),t.getIoType()) for t in db.findMaster(name).getMTerms()]) for name in ('BUF_X2','BUF_X4','BUF_X8','DFF_X1')}
 result[kind]=dict(dbu=block.getDbUnitsPerMicron(),die=[block.getDieArea().xMin(),block.getDieArea().yMin(),block.getDieArea().xMax(),block.getDieArea().yMax()],pins=pins,rows=rows,masters=masters,instances=len(block.getInsts()),net_count=len(block.getNets()))
 if kind=='m':
  result['api']={name:[s for s in dir(getattr(odb,name)) if not s.startswith('_')] for name in ('dbInst','dbWireEncoder','dbWire','dbBTerm','dbBPin','dbBox','dbTechVia','dbVia','dbRow','dbITerm')}
Path('physical-probe.json').write_text(json.dumps(result,indent=2)+'\\n')
'''.replace('CONFIG', repr(str(config)))
    (out / 'physical-probe.py').write_text(script)
    run(['openroad', '-no_init', '-exit', '-python', str(out / 'physical-probe.py')], 'physical-probe.log')
    help_script = '''set_thread_count 16
foreach cmd {detailed_route detailed_placement check_placement global_route repair_tie_fanout repair_design insert_buffer read_db read_lef write_verilog extract_parasitics} {
 puts "COMMAND $cmd"
 help $cmd
}
'''
    (out / 'tool-help.tcl').write_text(help_script)
    run(['openroad', '-no_init', '-exit', str(out / 'tool-help.tcl')], 'tool-help.log')
    result = json.loads((out / 'physical-probe.json').read_text())
    (out / 'linkclose-probe.json').write_text(json.dumps(dict(passed=True,
        native_sha256={k:r['hashes']['6_final.odb'] for k,r in native.items()},
        pin_counts={k:len(result[k]['pins']) for k in native},
        scope='Read-only native ODB and installed API inventory; no new physical qualification.'), indent=2)+'\n')


def probe(root,out,cpus,run):
    """The pinned binary has Tcl support, no embedded Python interpreter."""
    assert cpus==16
    native=json.loads((root/'project/experiments/block_v1/interconnect-sources.json').read_text())['macros']
    counts={}
    for kind,row in native.items():
        path=Path(row['verilog']).with_suffix('.odb')
        assert hashlib.sha256(path.read_bytes()).hexdigest()==row['hashes']['6_final.odb']
        script='set_thread_count 16\nread_db {'+str(path)+'}\n'
        script+='''set b [ord::get_db_block]
set f [open KIND-pins.tsv w]
foreach term [$b getBTerms] {
 if {[$term getSigType] in {POWER GROUND}} {continue}
 foreach pin [$term getBPins] {foreach box [$pin getBoxes] {
  puts $f "[$term getName]\\t[$term getIoType]\\t[[$box getTechLayer] getName]\\t[$box xMin]\\t[$box yMin]\\t[$box xMax]\\t[$box yMax]"
 }}
}
close $f
set f [open KIND-instances.tsv w]
foreach inst [$b getInsts] {
 set box [$inst getBBox]
 puts $f "[$inst getName]\\t[[$inst getMaster] getName]\\t[$inst getOrient]\\t[$inst getPlacementStatus]\\t[$box xMin]\\t[$box yMin]\\t[$box xMax]\\t[$box yMax]"
}
close $f
set f [open KIND-rows.tsv w]
foreach row [$b getRows] {
 puts $f "[$row getName]\\t[$row getOrigin]\\t[$row getOrient]\\t[$row getSiteCount]\\t[$row getSpacing]\\t[[$row getSite] getWidth]\\t[[$row getSite] getHeight]"
}
close $f
'''.replace('KIND',kind)
        (out/(kind+'-probe.tcl')).write_text(script)
        run(['openroad','-no_init','-exit',str(out/(kind+'-probe.tcl'))],kind+'-probe.log')
        counts[kind]=len((out/(kind+'-pins.tsv')).read_text().splitlines())
    text='set_thread_count 16\n'
    for cmd in ('detailed_route','detailed_placement','check_placement','global_route','insert_buffer','read_db','read_lef','write_verilog','extract_parasitics'):
        text+='puts {COMMAND '+cmd+'}\nhelp '+cmd+'\n'
    (out/'tool-help.tcl').write_text(text)
    run(['openroad','-no_init','-exit',str(out/'tool-help.tcl')],'tool-help.log')
    (out/'linkclose-probe.json').write_text(json.dumps(dict(passed=True,
        native_sha256={k:r['hashes']['6_final.odb'] for k,r in native.items()},pin_counts=counts,
        scope='Read-only accepted native ODB pin, instance, row and installed Tcl API inventory; no new physical qualification.'),indent=2)+'\n')
