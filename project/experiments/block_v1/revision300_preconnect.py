"""Bounded native M9/M10 corridor audit, without altering an accepted macro.

This is a resource diagnostic. Free rectangles alone never grant routed DRC,
timing, or array qualification. All obstacles include PG, clocks, pins and OBS.
"""
import json
import re
from pathlib import Path


def intersects(a,b,spacing=0):
    return (a[0]<b[2]+spacing and b[0]<a[2]+spacing and
            a[1]<b[3]+spacing and b[1]<a[3]+spacing)


def audit(root,out,cpus,run,kind):
    from io_slots import file_sha,slot
    assert cpus==16 and kind in ('m','t')
    base=out.parents[2]
    number='258' if kind=='m' else '256'
    geom=base/('block-v1-20261029-'+number)/'tasks'/('revision300-geometry-'+kind)
    receipt=json.loads((geom/'receipt.json').read_text())
    report=geom/'five-macro-geometry.json'
    assert receipt['passed'] and file_sha(report)==receipt['outputs'][report.name]
    proof=json.loads(report.read_text());assert proof['passed']
    # Read the exact accepted native DEF rather than inferring tracks from pitch.
    native=base/('block-v1-20261029-258' if kind=='m' else 'block-v1-20261028-249')/'tasks'/('revision300-final-source-'+kind)
    odb=native/'flow/results/nangate45'/('bv1_block_v1_'+kind)/'base/6_final.odb'
    deffile=odb.with_suffix('.def')
    source=json.loads((native/'receipt.json').read_text())
    assert source['passed']
    assert file_sha(deffile)==source['outputs'][str(deffile.relative_to(native))]
    assert file_sha(odb)==proof['source_odb_sha256']
    track={};dbu=None
    with deffile.open() as stream:
        for line in stream:
            m=re.match(r'UNITS DISTANCE MICRONS (\d+) ;',line)
            if m:dbu=int(m.group(1))
            m=re.match(r'TRACKS ([XY]) (\d+) DO (\d+) STEP (\d+) LAYER (metal9|metal10) ;',line)
            if m:
                axis,start,count,step,layer=m.groups()
                track[layer,axis]=[int(start)+i*int(step) for i in range(int(count))]
            if line.startswith('COMPONENTS'):break
    assert dbu==2000 and len(track)==4
    # Pinned native technology: use the worst PRL spacing table entry1.5um
    # for metal rather than underestimating spacing next to a wide PG stripe.
    tech=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef')
    text=tech.read_text()
    for layer,direction in [('metal9','HORIZONTAL'),('metal10','VERTICAL')]:
        block=text.split('LAYER '+layer+'\n',1)[1].split('END '+layer,1)[0]
        assert 'WIDTH 0.8 ;' in block and 'PITCH 1.6 ;' in block and 'DIRECTION '+direction+' ;' in block
        assert re.search(r'WIDTH 1.5000\s+0.8000\s+0.9000\s+1.5000',block)
    via=text.split('VIA via9_0 DEFAULT',1)[1].split('END via9_0',1)[0]
    assert via.count('RECT -0.4 -0.4 0.4 0.4 ;')==3
    cut=text.split('LAYER via9\n',1)[1].split('END via9',1)[0]
    assert 'SPACING 0.88 ;' in cut
    summary=dict(line.split('\t',1)for line in(geom/'native-summary.tsv').read_text().splitlines())
    die=list(map(int,summary['die'].split('\t')));assert die[:2]==[0,0] and die[2]==die[3]
    u=lambda x:int(x*dbu)
    x0=min(track['metal10','X'],key=lambda x:abs(x-u(40)))
    x1=min(track['metal10','X'],key=lambda x:abs(x-(die[2]-u(40))))
    low,high=die[3]//2-u(40),die[3]//2+u(40)
    candidates=[]
    for y in track['metal9','Y']:
        if low<=y<=high:
            candidates.append(dict(y=y,shapes=[
                ('metal9',[x0-u(.4),y-u(.4),x1+u(.4),y+u(.4)]),
                ('metal10',[x0-u(.4),y-u(.4),x0+u(.4),y+u(.4)]),
                ('metal10',[x1-u(.4),y-u(.4),x1+u(.4),y+u(.4)]),
                ('via9',[x0-u(.4),y-u(.4),x0+u(.4),y+u(.4)]),
                ('via9',[x1-u(.4),y-u(.4),x1+u(.4),y+u(.4)])],blockers=[]))
    aliases={};counts={};occupancy=geom/'source-occupancy.tsv'
    assert file_sha(occupancy)==receipt['outputs'][occupancy.name]
    with slot(base):
        for line in occupancy.open():
            if line.startswith('# NET '):
                _,_,alias,encoded=line.split();aliases[alias]=bytes.fromhex(encoded).decode();continue
            if line.startswith('#'):continue
            alias,layer,typ,*coords=line.rstrip('\n').split('\t')
            if layer not in ('metal9','metal10','via9'):continue
            box=list(map(int,coords));counts[layer]=counts.get(layer,0)+1
            for candidate in candidates:
                for target,shape in candidate['shapes']:
                    if layer!=target:continue
                    spacing=0 if 'obstruction' in typ else u(.88 if layer=='via9' else 1.5)
                    if intersects(shape,box,spacing):
                        # Keep every localized conflict, including duplicate shapes,
                        # to allow a reviewer to trace the exact native owner.
                        candidate['blockers'].append(dict(net=aliases[alias],alias=alias,layer=layer,
                            kind=typ,box_dbu=box,probe_box_dbu=shape,guard_dbu=spacing,
                            direct_overlap=intersects(shape,box)))
    chosen=[]
    for row in candidates:
        if row['blockers']:continue
        # Actual1.6um tracks alone fail the0.88um cut spacing: select at
        # least3.2um between via centers, not mechanically16*wire pitch.
        if chosen and row['y']-chosen[-1]['y']<u(3.2):continue
        chosen.append(row)
        if len(chosen)==16:break
    assert intersects([0,0,10,10],[9,9,11,11])
    assert not intersects([0,0,10,10],[10,0,20,10])
    assert intersects([0,0,10,10],[10,0,20,10],1)
    assert file_sha(odb)==proof['source_odb_sha256']
    result=dict(passed=True,macro=kind.upper(),stage='P3-resource-diagnostic',
        requested_bits=16,unblocked_candidate_bits=len(chosen),candidate_tracks=len(candidates),
        corridor_box_dbu=[x0,low,x1,high],dbu=dbu,die_dbu=die,
        native_track_axes={layer+'-'+axis:values for (layer,axis),values in track.items()},
        native_shape_counts=counts,selected_paths=chosen,candidates=candidates,
        metal_width_um=.8,conservative_metal_spacing_um=1.5,via9_cut_um=.8,
        via9_cut_spacing_um=.88,selected_center_spacing_um=3.2,
        native_geometry_report_sha256=file_sha(report),native_receipt_sha256=file_sha(geom/'receipt.json'),
        native_occupancy_sha256=file_sha(occupancy),native_odb_sha256=file_sha(odb),
        native_def_sha256=file_sha(deffile),native_technology_sha256=file_sha(tech),
        fixed_routes_created=False,full_native_drc_qualified=False,p3_qualified=False,
        scope='Exact accepted native occupancy/DEF tracks and pinned native via9 rules. Finite straight16bit horizontal corridor across the central80um band,40um inset endpoints. Conservative1.5um metal guard may reject legal PRL cases. No route database, DRC or timing qualification; no proof that arbitrary detours or other corridor locations fail. Accepted native macro unchanged.')
    (out/'revision300-preconnect.json').write_text(json.dumps(result,indent=2)+'\n')
