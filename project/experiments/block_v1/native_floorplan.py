"""Import exact candidate netlists and place IO windows, leaving cells unplaced.

This is a physical input/access feasibility probe, not P3 hardening.
No optimizer, PG, CTS, signal routing or estimated timing acceptance runs here.
"""
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(root,out,run,top,policy,pipeline='native_pipeline.json'):
    assert top in ('shared109','transaction6k') and policy in ('A','C')
    assert pipeline in ('native_pipeline.json','native_pipeline_const.json')
    config=json.loads((root/'project/experiments/block_v1'/pipeline).read_text())
    base=out.parents[2]
    source=base/config['preparation_run']/'tasks/native-prepare'
    receipt=json.loads((source/'receipt.json').read_text());assert receipt['passed']is True
    path=source/'native-preparation.json';assert sha(path)==receipt['outputs'][path.name]
    data=json.loads(path.read_text())
    candidate=next(c for c in data['candidates']if c['top']==top and c['policy']==policy)
    folder=Path(candidate['folder']);inputs=source/'inputs'/top
    for path in [folder/'pins.json',folder/'pins.tcl',inputs/(top+'.v'),inputs/(top+'.sdc')]:
        assert sha(path)==receipt['outputs'][str(path.relative_to(source))]
    budget=candidate['budget'];w,h=budget['die_um'];m=budget['core_margin_um']
    platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
    script='read_liberty {'+str(platform/'lib/NangateOpenCellLibrary_typical.lib')+'}\n'
    for name in ['NangateOpenCellLibrary.tech.lef','NangateOpenCellLibrary.macro.mod.lef']:
        script+='read_lef {'+str(platform/'lef'/name)+'}\n'
    script+='read_verilog {'+str(inputs/(top+'.v'))+'}\nlink_design '+top+'\n'
    script+='read_sdc {'+str(inputs/(top+'.sdc'))+'}\nreport_units\nwrite_sdc constraints-readback.sdc\n'
    script+='initialize_floorplan -die_area {0 0 %g %g} -core_area {%g %g %g %g} -site FreePDK45_38x28_10R_NP_162NW_34O\n'%(w,h,m,m,w-m,h-m)
    script+='source {'+str(platform/'make_tracks.tcl')+'}\nsource {'+str(folder/'pins.tcl')+'}\n'
    script+=r'''
set block [ord::get_db_block]
set scale [$block getDbUnitsPerMicron]
set stream [open observed-pins.tsv w]
foreach term [$block getBTerms] {
  foreach pin [$term getBPins] {
    foreach box [$pin getBoxes] {
      puts $stream "[$term getName]\t[[$box getTechLayer] getName]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"
    }
  }
}
close $stream
set area 0
set count 0
foreach inst [$block getInsts] {
  set master [$inst getMaster]
  set area [expr {$area+wide([$master getWidth])*[$master getHeight]}]
  incr count
}
set stream [open initial-inventory.tsv w]
puts $stream "$count\t[expr {$area/double($scale*$scale)}]"
close $stream
write_db prepared.odb
write_def prepared.def
'''
    script+='set ::env(BV1_UNDRIVEN_REPORT) {used-signal-drivers.tsv}\n'
    script+='source {'+str(root/'project/experiments/block_v1/native_undriven.tcl')+'}\n'
    (out/'prepare.tcl').write_text(script)
    run(['openroad','-no_init','-exit','prepare.tcl'],'prepare.log')
    from native_driver_report import inspect as driver_audit
    drivers=driver_audit((out/'used-signal-drivers.tsv').read_text())
    assert drivers['passed'],'Imported source contains used nets without real drivers'
    wanted={p['pin']:p for p in json.loads((folder/'pins.json').read_text())['pins']}
    got={}
    for line in(out/'observed-pins.tsv').read_text().splitlines():
        name,layer,*values=line.split('\t');assert name not in got
        got[name]=(layer,list(map(int,values)))
    assert set(got)==set(wanted)
    for name,pin in wanted.items():
        layer,box=got[name];x,y=pin['xy_um'];pw,ph=pin['size_um']
        expected=[round(v*2000)for v in [x-pw/2,y-ph/2,x+pw/2,y+ph/2]]
        assert layer=='metal10' and box==expected,(name,box,expected)
    # Independently inspect the actual exported database track grammar.
    # Stop after NETS begins; do not load the complete large DEF into RAM.
    tracks={}
    import re
    with(out/'prepared.def').open()as stream:
        for line in stream:
            line=line.strip()
            if line.startswith('NETS '):break
            if not line.startswith('TRACKS '):continue
            match=re.fullmatch(r'TRACKS ([XY]) (\d+) DO (\d+) STEP (\d+) LAYER (\S+) ;\s*',line)
            assert match,('Unrecognized actual DEF track',line)
            axis,origin,number,step,layer=match.groups()
            if layer not in ('metal9','metal10'):continue
            assert (layer,axis)not in tracks
            tracks[layer,axis]=tuple(map(int,[origin,number,step]))
    assert set(tracks)=={(m,a)for m in ['metal9','metal10']for a in ['X','Y']}
    def aligned(pins):
        for p in pins:
            for axis,coordinate in zip(['X','Y'],p['xy_um']):
                center=round(coordinate*2000);origin,number,step=tracks['metal10',axis]
                if (center-origin)%step or not 0<=(center-origin)//step<number:return False
        return True
    assert aligned(list(wanted.values())),'Planned pin misses actual native DB track grid'
    old=base/'block-v1-20261027-054/tasks/native-prepare'
    old_receipt=json.loads((old/'receipt.json').read_text());assert old_receipt['passed']is True
    old_path=old/(top+'-'+policy)/'pins.json'
    assert sha(old_path)==old_receipt['outputs'][str(old_path.relative_to(old))]
    assert not aligned(json.loads(old_path.read_text())['pins']),'Old .8-offset negative unexpectedly aligned'
    count,area=(out/'initial-inventory.tsv').read_text().split()
    assert int(count)>0 and 0<float(area)<=budget['max_stdcell_area_um2']
    (out/'native-floorplan-input.json').write_text(json.dumps(dict(schema='block-v1-native-floorplan-input/1',
        top=top,policy=policy,ports=len(wanted),exact_m10_boxes=True,
        initial_mapped_cells=int(count),initial_area_um2=float(area),source=str(source),
        actual_native_tracks={m+':'+a:v for (m,a),v in tracks.items()},all_pins_track_aligned=True,
        old_offset_negative_rejected=True,
        used_signal_driver_audit=drivers,
        used_signal_driver_report_sha256=sha(out/'used-signal-drivers.tsv'),
        source_receipt_sha256=sha(source/'receipt.json'),passed=True,
        qualification='Input import, unplaced cell inventory, die/core rows and exact fixed pin boxes only; PG/placement/CTS/route/STA/RC unqualified'),indent=2)+'\n')
