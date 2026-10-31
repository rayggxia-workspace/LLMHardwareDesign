"""Read-only final native occupancy and M10 landing geometry for the five leaves.

This exports the already accepted leaf. It does not qualify an abstract timing
model, an upper-layer route, or a twelve-layer design.
"""
from collections import Counter
from decimal import Decimal
import json
from pathlib import Path


def access_contract(rows,dbu,technology,allow_zero_enclosure=False):
    """Place the declared via10 bottom enclosure wholly inside each real BPin."""
    def units(value):
        n=Decimal(str(value))*dbu
        assert n==int(n)
        return int(n)
    cut=units(technology['geometry_um']['cut_width'])
    enclosure=units(technology['geometry_um']['enclosure'])
    assert cut>0 and (enclosure>0 or (allow_zero_enclosure and enclosure==0)) and cut%2==0
    if allow_zero_enclosure:
        assert technology['schema']=='block-v1-coarse-demo-stack/1'
        assert technology['model']=='ideal-alignment-research-demo'
        assert technology['qualification']['manufacturing_validated'] is False
    seen=set();access=[]
    for row in rows:
        name,layer,box=row['pin'],row['layer'],row['box_dbu']
        assert name not in seen and layer=='metal10';seen.add(name)
        a,b,c,d=box
        assert all(type(v)is int for v in box) and a<c and b<d
        assert (a+c)%2==0 and (b+d)%2==0
        x,y=(a+c)//2,(b+d)//2
        q=[x-cut//2,y-cut//2,x+cut//2,y+cut//2]
        bottom=[q[0]-enclosure,q[1]-enclosure,q[2]+enclosure,q[3]+enclosure]
        assert a<=bottom[0]<bottom[2]<=c and b<=bottom[1]<bottom[3]<=d
        access.append(dict(pin=name,net=row['net'],layer=layer,box_dbu=box,
                           center_dbu=[x,y],via10_cut_dbu=q,bottom_enclosure_dbu=bottom))
    assert access
    return access


def accepted(root,out,kind):
    from io_slots import file_sha
    base=out.parents[2]
    if kind=='t':
        p=root/'project/experiments/block_v1/five_macro_t_source.json'
        index=json.loads(p.read_text())
        assert index['passed'] and index['selected']=='transaction6k-C'
        assert index['native_standalone_physical_pass'] and index['final_netlist_function_pass']
        assert index['independent_drc_items']==0
        odb=Path(index['final_files']['6_final.odb']['path']);source=odb.parents[5]
        assert base in source.parents
        r=json.loads((source/'receipt.json').read_text());assert r['passed']
        assert file_sha(source/'receipt.json')==index['source_receipt_sha256']
        for name,f in index['final_files'].items():
            path=Path(f['path']);assert file_sha(path)==f['sha256']
        return index,odb,dict(index_path=str(p),index_sha256=file_sha(p),
                              source_receipt_sha256=index['source_receipt_sha256']),386,[1120,1120]
    number=dict(m='203',v='228',s='225',r='208')[kind]
    mode='five-macro-delivery-'+kind if kind in ('m','v','s') else 'five-macro-delivery-received-'+kind
    folder=base/('block-v1-20261027-'+number)/'tasks'/mode
    receipt=json.loads((folder/'receipt.json').read_text());assert receipt['passed'] and receipt['mode']==mode
    p=folder/'five-macro-delivery.json';assert file_sha(p)==receipt['outputs'][p.name]
    index=json.loads(p.read_text());assert index['passed'] and index['native_leaf_accepted']
    assert index['implementation_count']==1 and index['macro']==kind.upper()
    assert set(index['gate_receipts'])=={'physical','drc','final-function','formal'}
    for gate in index['gate_receipts'].values():
        r=Path(gate['path']);q=Path(gate['report_path'])
        assert base in r.parents and q.parent==r.parent
        assert file_sha(r)==gate['sha256'] and file_sha(q)==gate['report_sha256']
        bound=json.loads(r.read_text());proof=json.loads(q.read_text())
        assert bound['passed'] and proof['passed'] and bound['outputs'][q.name]==file_sha(q)
        assert proof['source_receipt_sha256']==index['source_receipt_sha256']
    odb=Path(index['final_files']['6_final.odb']['path'])
    assert base in odb.parents and file_sha(odb)==index['final_files']['6_final.odb']['sha256']
    return index,odb,dict(delivery_receipt_path=str(folder/'receipt.json'),
                         delivery_receipt_sha256=file_sha(folder/'receipt.json'),
                         delivery_report_sha256=file_sha(p)),index['pins']['signal_bits'],index['die_um']


def export(root,out,cpus,run,kind,selected=None,technology_name='technology.json',allow_zero_enclosure=False):
    from io_slots import file_sha,slot
    assert cpus==16 and kind in ('m','n','e','g','r','s','t')
    receive=accepted if selected is None else selected
    index,odb,provenance,count,die=receive(root,out,kind)
    before=file_sha(odb)
    helper=root/'project/experiments/block_v1/odb_geometry.tcl'
    technology_path=root/'project/experiments/block_v1'/technology_name
    technology=json.loads(technology_path.read_text())
    script='set_thread_count 16\nread_db {'+str(odb)+'}\nsource {'+str(helper)+'}\n'
    script+='''set block [ord::get_db_block]
bvgeom::export source-occupancy.tsv
set f [open native-summary.tsv w]
puts $f "dbu\\t[$block getDbUnitsPerMicron]"
puts $f "top\\t[$block getName]"
set die [$block getDieArea]
puts $f "die\\t[$die xMin]\\t[$die yMin]\\t[$die xMax]\\t[$die yMax]"
close $f
set f [open native-pins.tsv w]
foreach term [$block getBTerms] {
  set net [$term getNet]
  if {![bvgeom::present $net]} {error "Unconnected native port"}
  foreach pin [$term getBPins] {
    foreach box [$pin getBoxes] {
      if {[$box isVia]} {error "Via-shaped native BPin requires explicit expansion"}
      puts $f "[$term getName]\\t[$term getIoType]\\t[$term getSigType]\\tn[$net getId]\\t[[$box getTechLayer] getName]\\t[$box xMin]\\t[$box yMin]\\t[$box xMax]\\t[$box yMax]"
    }
  }
}
close $f
set f [open source-occupancy.tsv a]
set instances 0;set master_boxes 0;set block_boxes 0
foreach instance [$block getInsts] {
  incr instances
  set owner i[$instance getId]
  puts $f "# NET $owner [binary encode hex [encoding convertto utf-8 @instance/[$instance getName]]]"
  set transform [$instance getTransform]
  foreach box [[$instance getMaster] getObstructions] {
    incr master_boxes
    bvgeom::db_box $f $owner $box instance-obstruction $transform
  }
}
foreach obstruction [$block getObstructions] {
  incr block_boxes
  bvgeom::db_box $f block-obstruction [$obstruction getBBox] block-obstruction
}
close $f
set f [open occupancy-summary.tsv w]
puts $f "instances\\t$instances"
puts $f "master_obstruction_boxes\\t$master_boxes"
puts $f "block_obstruction_boxes\\t$block_boxes"
close $f
write_abstract_lef -bloat_occupied_layers candidate.lef
'''
    (out/'export.tcl').write_text(script)
    with slot(out.parents[2]):
        run(['openroad','-no_init','-exit',str(out/'export.tcl')],'export.log')
    from native_rect_completion import complement
    source_def=Path(index['final_files']['6_final.def']['path'])
    assert file_sha(source_def)==index['final_files']['6_final.def']['sha256']
    rects=complement(out/'source-occupancy.tsv',source_def,kind,require_historic_m_patch=selected is None)
    (out/'native-rect-completion.json').write_text(json.dumps(rects,indent=2)+'\n')
    summary=dict(line.split('\t',1)for line in(out/'native-summary.tsv').read_text().splitlines())
    dbu=int(summary['dbu']);assert dbu==2000
    assert list(map(int,summary['die'].split('\t')))==[0,0,int(die[0]*dbu),int(die[1]*dbu)]
    pins=[];pg=[]
    for line in(out/'native-pins.tsv').read_text().splitlines():
        name,direction,sigtype,net,layer,*box=line.split('\t')
        row=dict(pin=name,direction=direction,sigtype=sigtype,net=net,layer=layer,box_dbu=list(map(int,box)))
        (pg if sigtype in ('POWER','GROUND')else pins).append(row)
    assert len(pins)==len({p['pin']for p in pins})==count
    assert {p['sigtype']for p in pg}=={'POWER','GROUND'}
    if kind!='t' or selected is not None:
        p=Path(index['pins']['path']);assert file_sha(p)==index['pins']['sha256']
        wanted=json.loads(p.read_text())['pins']
        assert {p['pin']:(p['layer'],tuple(p['box_dbu']))for p in pins}=={p['pin']:(p['layer'],tuple(p['box_dbu']))for p in wanted}
    access=access_contract(pins,dbu,technology,allow_zero_enclosure)
    rejected={}
    import copy
    for label in ('undersized_landing','wrong_layer','noninteger_center'):
        bad=copy.deepcopy(pins)
        if label=='undersized_landing':bad[0]['box_dbu'][2]-=10
        elif label=='wrong_layer':bad[0]['layer']='metal9'
        else:bad[0]['box_dbu'][2]-=1
        rejected[label]=False
        try:access_contract(bad,dbu,technology,allow_zero_enclosure)
        except AssertionError:rejected[label]=True
    assert all(rejected.values())
    # Stream the complete geometry; do not turn native OBS into conductors or
    # crop the source to a pin window. Net identities are retained throughout.
    counts=Counter();layers=Counter();ports=Counter()
    allowed={'metal'+str(i)for i in range(1,11)}|{'via'+str(i)for i in range(1,10)}
    with(out/'source-occupancy.tsv').open()as stream:
        for line in stream:
            if line.startswith('#'):continue
            net,layer,typ,*box=line.rstrip('\n').split('\t')
            assert layer in allowed and len(box)==4
            a,b,c,d=map(int,box);assert a<c and b<d
            counts[typ]+=1;layers[layer]+=1
            if typ=='block-port':ports[(net,layer,a,b,c,d)]+=1
    for p in pins+pg:assert ports[(p['net'],p['layer'],*p['box_dbu'])]>0
    assert counts['wire']>0 and counts['instance-obstruction']>0 and counts['instance-pin']>0
    (out/'m10-access.json').write_text(json.dumps(dict(dbu_per_um=dbu,die_um=die,pins=access,
        geometry_only=True,technology_sha256=file_sha(technology_path),negative_controls=rejected,
        future_m11_m12_system_qualified=False),indent=2)+'\n')
    assert file_sha(odb)==before
    assert receive(root,out,kind)[1]==odb
    files={}
    for name in ('source-occupancy.tsv','native-pins.tsv','occupancy-summary.tsv','m10-access.json','candidate.lef','native-rect-completion.json'):
        p=out/name;assert p.stat().st_size>0
        files[name]=dict(path=str(p),sha256=file_sha(p),bytes=p.stat().st_size)
    result=dict(passed=True,macro=kind.upper(),top=summary['top'],source_odb=str(odb),source_odb_sha256=before,
                provenance=provenance,geometry_helper_sha256=file_sha(helper),die_um=die,signal_bits=count,
                native_geometry_counts=dict(counts),native_layer_counts=dict(layers),files=files,
                original_odb_unchanged=True,native_def_rect_complete=True,rect_completion=rects,
                abstract_coverage_qualified=False,hierarchical_lib_qualified=False,
                m11_m12_system_qualified=False,
                scope='Complete read-only native wire/via/PG/instance-pin/master-and-block-OBS export and geometric via10 bottom fit. Candidate LEF only; no abstract coverage, hierarchical timing or upper-layer routing qualification.')
    (out/'five-macro-geometry.json').write_text(json.dumps(result,indent=2)+'\n')
