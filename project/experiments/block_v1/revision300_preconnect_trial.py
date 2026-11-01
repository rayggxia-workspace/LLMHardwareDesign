"""One bounded wider-corridor experiment; add actual native paths only to a copy."""
from collections import defaultdict
import json
from pathlib import Path


def linked(rows):
    """Check left/right M10 endpoint shapes through actual M9/via9 geometry."""
    ports=[i for i,x in enumerate(rows) if x[1]=='block-port']
    assert len(ports)==2
    def edge(a,b):
        la,_,aa=a;lb,_,bb=b
        layers=la==lb or {la,lb} in ({'via9','metal9'},{'via9','metal10'})
        return layers and aa[0]<bb[2] and bb[0]<aa[2] and aa[1]<bb[3] and bb[1]<aa[3]
    seen={ports[0]};todo=list(seen)
    while todo:
        a=todo.pop()
        for b in range(len(rows)):
            if b not in seen and edge(rows[a],rows[b]):
                seen.add(b);todo.append(b)
    return ports[1] in seen


def trial(root,out,cpus,run,kind):
    from io_slots import file_sha
    from revision300_preconnect import audit
    from native_escape import records
    from native_rect_completion import rectangles
    audit(root,out,cpus,run,kind,band_um=240,landing_um=2.,center_spacing_um=4.8)
    p=out/'revision300-preconnect.json';diagnostic=json.loads(p.read_text())
    result=dict(passed=False,macro=kind.upper(),requested_bits=16,
        resource_diagnostic_sha256=file_sha(p),original_unchanged=True,
        production_macro_changed=False,full_leaf_qualified=False,p3_qualified=False,
        scope='Single240um band after80um diagnostic failed16bits. Native M9 wires and native via9/M10 endpoint pads only in a disposable risk-test copy, not a new production macro or array. Exact declared geometry only; no timing/system/manufacturing qualification.')
    def save():(out/'revision300-preconnect-trial.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    if diagnostic['unblocked_candidate_bits']!=16:
        result.update(passed=True,resource_insufficient=True,
            fixed_routes_created=False,reason='Conservative declared240um band still cannot fit16 full-width landing paths; exact blockers in diagnostic, not proof against other positions/PRL/detours.')
        save();return
    base=out.parents[2]
    native=base/('block-v1-20261029-258' if kind=='m' else 'block-v1-20261028-249')/'tasks'/('revision300-final-source-'+kind)
    top='bv1_block_v1_m' if kind=='m' else 'bv1_transaction6k'
    odb=native/'flow/results/nangate45'/top/'base/6_final.odb'
    before=file_sha(odb);assert before==diagnostic['native_odb_sha256']
    script='set_thread_count 16\nread_db {'+str(odb)+'}\nset block [ord::get_db_block]\nset tech [ord::get_db_tech]\n'
    script+='set via [$tech findVia via9_0]\nif {$via eq "NULL"} {error "Native via9 missing"}\n'
    x0,_,x1,_=diagnostic['corridor_box_dbu']
    for i,row in enumerate(diagnostic['selected_paths']):
        y=row['y'];name='bv1_p3_probe_'+str(i)
        script+='''if {[$block findNet %s] ne "NULL"} {error "Probe net already exists"}
set net [odb::dbNet_create $block %s]
set wire [odb::dbWire_create $net]
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_begin $enc $wire
odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc %d %d
odb::dbWireEncoder_addPoint $enc %d %d
'''%(name,name,x0,y,x1,y)
        for side,x in [('left',x0),('right',x1)]:
            script+='''odb::dbWireEncoder_newPath $enc [$tech findLayer metal9] ROUTED
odb::dbWireEncoder_addPoint $enc %d %d
odb::dbWireEncoder_addTechVia $enc $via
odb::dbWireEncoder_newPath $enc [$tech findLayer metal10] ROUTED
odb::dbWireEncoder_addPoint $enc %d %d
odb::dbWireEncoder_addRect $enc -2000 -2000 2000 2000
set port [odb::dbBTerm_create $net %s_%s]
$port setIoType %s
set pin [odb::dbBPin_create $port]
$pin setPlacementStatus FIRM
odb::dbBox_create $pin [$tech findLayer metal10] %d %d %d %d
'''%(x,y,x,y,name,side,'INPUT' if side=='left' else 'OUTPUT',x-2000,y-2000,x+2000,y+2000)
        script+='odb::dbWireEncoder_end $enc\nodb::delete_dbWireEncoder $enc\n'
    helper=(root/'project/experiments/block_v1/odb_geometry.tcl').read_text()
    needle='  foreach net [$block getNets] {';assert helper.count(needle)==1
    helper=helper.replace(needle,'''  set selected {}
  foreach candidate [$block getNets] {
    if {[string match bv1_p3_probe_* [$candidate getName]]} {lappend selected $candidate}
  }
  if {[llength $selected]!=16} {error "Missing probe net"}
  foreach net $selected {''')
    (out/'probe-geometry.tcl').write_text(helper)
    script+='write_db probe.odb\nwrite_def probe.def\nsource {'+str(out/'probe-geometry.tcl')+'}\nbvgeom::export probe-geometry.tsv\n'
    script+='drt::check_drc_cmd probe-native-drc.rpt 0 0 0 0 native_whole_drc\n'
    (out/'probe.tcl').write_text(script)
    run(['openroad','-no_init','-exit',out/'probe.tcl'],'probe.log')
    aliases={};by_net=defaultdict(list)
    for line in (out/'probe-geometry.tsv').read_text().splitlines():
        if line.startswith('# NET '):
            _,_,alias,encoded=line.split();aliases[alias]=bytes.fromhex(encoded).decode()
        elif not line.startswith('#'):
            alias,layer,typ,*box=line.split('\t');by_net[aliases[alias]].append((layer,typ,list(map(int,box))))
    rects=[]
    for record in records(out/'probe.def'):
        if record.lstrip().startswith('- bv1_p3_probe_ '):raise AssertionError('Ambiguous net')
        name=record.lstrip().split()[1]
        if name.startswith('bv1_p3_probe_'):
            for name,layer,a,b,c,d in rectangles(record):
                rects.append((name,layer,a,b,c,d));by_net[name].append((layer,'wire-rect',[a,b,c,d]))
    assert len(rects)==32 and len(by_net)==16
    assert all(linked(rows) for rows in by_net.values())
    first=next(iter(by_net.values()))
    assert not linked([r for r in first if r[0]!='via9']), 'Missing-via negative was not rejected'
    drc=(out/'probe-native-drc.rpt').read_text();violations=drc.count('violation type:')
    assert file_sha(odb)==before
    result.update(passed=violations==0,fixed_routes_created=True,
        simultaneous_connected_bits=len(by_net),actual_rects=rects,
        native_drc_count=violations,missing_via_negative_rejected=True,
        original_odb_sha256=before,probe_odb_sha256=file_sha(out/'probe.odb'),
        probe_def_sha256=file_sha(out/'probe.def'),
        p3_qualified=violations==0,qualification_scope='Declared16bit local geometric risk trial and native whole-chip DRC only; not adopted in the accepted production macro, full GDS/STA/final qualification not transferred.')
    save()
    assert result['passed'],'Actual fixed-route trial has native DRC; preserve failure'
