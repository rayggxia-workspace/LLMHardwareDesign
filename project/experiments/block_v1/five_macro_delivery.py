"""Read-only delivery views of selected, real T6K C geometry."""
import json
from pathlib import Path


def final_leaf(root,out,cpus,run,kind,gate_roots=None):
    """Index and render a new leaf only after all its exact final gates pass."""
    from io_slots import file_sha
    from five_macro_receive import source
    assert cpus==16 and kind in ('m','v','r','s')
    folder,r,flow,results=source(out,kind)
    proofs={};receipts={}
    for stage,report in [('physical','five-macro-physical.json'),('drc','five-macro-drc.json'),
                         ('final-function','five-macro-final-function.json'),('formal','five-macro-formal.json')]:
        gate_root=(gate_roots or {}).get(stage,out.parent)
        assert gate_root.name=='tasks' and gate_root.parent.parent==out.parents[2]
        parent=gate_root/('five-macro-'+stage+'-'+kind)
        receipt=json.loads((parent/'receipt.json').read_text());assert receipt['passed'] is True
        path=parent/report;assert file_sha(path)==receipt['outputs'][report]
        proof=json.loads(path.read_text());assert proof['passed'] is True
        assert proof['source_receipt_sha256']==file_sha(folder/'receipt.json')
        proofs[stage]=proof
        receipts[stage]=dict(path=str(parent/'receipt.json'),sha256=file_sha(parent/'receipt.json'),
                             report_path=str(path),report_sha256=file_sha(path))
    gds=Path(proofs['drc']['gds']['path']);assert file_sha(gds)==proofs['drc']['gds']['sha256']
    assert proofs['drc']['full_deck']['total_items']==0 and not proofs['drc']['native_report'].strip()
    assert all(proofs['physical']['checks'].values()) and proofs['formal']['strict_native_lec']['passed']
    assert len(proofs['final-function']['initial_runs'])==3
    assert proofs['formal']['source_final_function_receipt_sha256']==receipts['final-function']['sha256']
    # These are actual native pins, not the planned XY list or a picture.
    script='read_db {'+str(results/'6_final.odb')+'}\nset f [open pins.tsv w]\n'
    script+='foreach p [[ord::get_db_block] getBTerms] {if {[$p getSigType] in {POWER GROUND}} {continue}; foreach pin [$p getBPins] {foreach b [$pin getBoxes] {puts $f "[$p getName]|[[$b getTechLayer] getName]|[$b xMin]|[$b yMin]|[$b xMax]|[$b yMax]"}}}\nclose $f\n'
    script+='set f [open dbu.txt w]; puts $f [[ord::get_db_block] getDbUnitsPerMicron];close $f\n'
    (out/'pins.tcl').write_text(script);run(['openroad','-no_init','-exit',str(out/'pins.tcl')],'pins.log')
    dbu=int((out/'dbu.txt').read_text());assert dbu==2000
    pins=[]
    for line in (out/'pins.tsv').read_text().splitlines():
        name,layer,*box=line.split('|');box=list(map(int,box))
        assert layer=='metal10' and box[2]-box[0]==1600 and box[3]-box[1]==1600
        pins.append(dict(pin=name,layer=layer,box_dbu=box,box_um=[v/dbu for v in box]))
    wanted=json.loads((folder/'pins.json').read_text())['pins']
    assert len(pins)==len({p['pin'] for p in pins})==len(wanted)
    assert {p['pin'] for p in pins}=={p['pin'] for p in wanted}
    (out/'pins.json').write_text(json.dumps(dict(dbu_per_um=dbu,pins=pins),indent=2)+'\n')
    image=out/(flow['top']+'.png')
    script='''import pya
view=pya.LayoutView()
view.load_layout(INPUT,0)
view.max_hier()
view.add_missing_layers()
view.zoom_fit()
view.save_image(OUTPUT,1600,1600)
'''.replace('INPUT',repr(str(gds))).replace('OUTPUT',repr(str(image)))
    (out/'render.py').write_text(script)
    run(['env','QT_QPA_PLATFORM=offscreen','klayout','-z','-r',str(out/'render.py')],'layout.log')
    assert image.stat().st_size>1000
    files={}
    for path in [results/('6_final.'+suffix) for suffix in ('v','sdc','def','odb','spef')]+[gds]:
        files[path.name]=dict(path=str(path),sha256=file_sha(path),bytes=path.stat().st_size)
    assert source(out,kind)[1]==r
    result=dict(passed=True,macro=kind.upper(),top=flow['top'],implementation_count=1,
                native_leaf_accepted=True,native_routing_layers=['metal'+str(i) for i in range(1,11)],
                die_um=flow['die_um'],active_area_um2=proofs['physical']['active_area_um2'],
                physical_only_area_um2=proofs['physical']['physical_only_area_um2'],
                final_files=files,source_receipt_sha256=file_sha(folder/'receipt.json'),gate_receipts=receipts,
                pins=dict(path=str(out/'pins.json'),sha256=file_sha(out/'pins.json'),signal_bits=len(pins)),
                image=dict(path=str(image),sha256=file_sha(image),bytes=image.stat().st_size),
                qualified_hard_macro=False,hierarchical_lib_qualified=False,m11_m12_system_qualified=False,
                scope='One actual final native M1-M10 leaf; all same-source physical/full native and full GDS deck/function/strict LEC gates pass. Hierarchical timing-model and M11/M12-system qualification are separate and unclaimed.')
    (out/'five-macro-delivery.json').write_text(json.dumps(result,indent=2)+'\n')


def received_leaf(root,out,cpus,run,kind):
    """Fresh exact-pin physical gate; other gates bind the same unchanged source."""
    assert kind in ('s','r','v')
    original=out.parents[2]/'block-v1-20261027-207/tasks'
    final_leaf(root,out,cpus,run,kind,gate_roots={stage:original for stage in ('drc','final-function','formal')})


def selected(root,key):
    from io_slots import file_sha
    index=root/'project/experiments/block_v1/five_macro_t_source.json'
    data=json.loads(index.read_text());assert data['selected']=='transaction6k-C'
    record=data['final_files'][key];path=Path(record['path'])
    assert file_sha(path)==record['sha256'] and path.stat().st_size==record['bytes']
    return path,record,index


def pins(root,out,cpus,run):
    from io_slots import file_sha
    assert cpus==16
    odb,source,index=selected(root,'6_final.odb')
    script='read_db {'+str(odb)+'}\nset f [open pins.tsv w]\n'
    script+='foreach p [[ord::get_db_block] getBTerms] {if {[$p getSigType] in {POWER GROUND}} {continue}; foreach pin [$p getBPins] {foreach b [$pin getBoxes] {puts $f "[$p getName]|[[$b getTechLayer] getName]|[$b xMin]|[$b yMin]|[$b xMax]|[$b yMax]"}}}\nclose $f\n'
    script+='set f [open dbu.txt w]; puts $f [[ord::get_db_block] getDbUnitsPerMicron];close $f\n'
    (out/'pins.tcl').write_text(script);run(['openroad','-no_init','-exit',str(out/'pins.tcl')],'pins.log')
    dbu=int((out/'dbu.txt').read_text().strip());rows=[]
    for line in (out/'pins.tsv').read_text().splitlines():
        name,layer,*coords=line.split('|');coords=list(map(int,coords))
        assert layer=='metal10' and coords[2]-coords[0]>=round(.8*dbu) and coords[3]-coords[1]>=round(.8*dbu)
        rows.append(dict(pin=name,layer=layer,box_dbu=coords,box_um=[c/dbu for c in coords]))
    assert len({p['pin'] for p in rows})==386
    result=dict(passed=True,selected='transaction6k-C',source_index_sha256=file_sha(index),source_odb=source,
                dbu_per_um=dbu,pins=rows,signal_bits=386,
                scope='Actual selected ODB signal pin geometry; no new timing or future M11/via10 access qualification')
    (out/'five-macro-t-pins.json').write_text(json.dumps(result,indent=2)+'\n')


def layout(root,out,cpus,run):
    from io_slots import file_sha
    assert cpus==16
    gds,source,index=selected(root,'native-full.gds')
    script='''import pya
view=pya.LayoutView()
view.load_layout(INPUT,0)
view.max_hier()
view.add_missing_layers()
view.zoom_fit()
view.save_image(OUTPUT,1600,1600)
'''.replace('INPUT',repr(str(gds))).replace('OUTPUT',repr(str(out/'transaction6k-C.png')))
    (out/'render.py').write_text(script)
    run(['env','QT_QPA_PLATFORM=offscreen','klayout','-z','-r',str(out/'render.py')],'layout.log')
    image=out/'transaction6k-C.png';assert image.is_file() and image.stat().st_size>1000
    result=dict(passed=True,selected='transaction6k-C',source_index_sha256=file_sha(index),source_gds=source,
                image_sha256=file_sha(image),image_bytes=image.stat().st_size,
                scope='Read-only full selected final GDS rendering, all layers, 1600x1600; image is not a DRC acceptance')
    (out/'five-macro-t-layout.json').write_text(json.dumps(result,indent=2)+'\n')
