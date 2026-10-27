"""Read-only delivery views of selected, real T6K C geometry."""
import json
from pathlib import Path


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
