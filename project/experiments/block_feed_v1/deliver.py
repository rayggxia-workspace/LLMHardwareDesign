"""Deliver actual native leaves only after all exact-source independent gates."""
import json
from pathlib import Path
import shutil
from io_slots import file_sha as sha
from qualify import ROOT, source


def accepted(folder):
    receipt=json.loads((folder/'receipt.json').read_text());assert receipt['passed']
    f=folder/'delivery.json';assert sha(f)==receipt['outputs'][f.name]
    index=json.loads(f.read_text());assert index['passed'] and index['native_leaf_accepted']
    for row in index['final_files'].values():assert sha(row['path'])==row['sha256']
    for row in index['gate_receipts'].values():
        assert sha(row['path'])==row['sha256'] and sha(row['report_path'])==row['report_sha256']
    return index


def deliver(folder,out,run,gates):
    folder,r,flow,results=source(folder);macro='m' if flow['top']=='block_feed_m' else 's'
    proofs={};receipts={}
    reports={'physical':'five-macro-physical.json','drc':'five-macro-drc.json','function':'final-function.json','formal':'formal.json'}
    for op,name in reports.items():
        p=gates/(op+'-'+macro);receipt=json.loads((p/'receipt.json').read_text());assert receipt['passed']
        assert sha(p/name)==receipt['outputs'][name]
        proof=json.loads((p/name).read_text());assert proof['passed'] and proof['source_receipt_sha256']==sha(folder/'receipt.json')
        proofs[op]=proof;receipts[op]=dict(path=str(p/'receipt.json'),sha256=sha(p/'receipt.json'),report_path=str(p/name),report_sha256=sha(p/name))
    assert proofs['drc']['full_deck']['total_items']==0 and not proofs['drc']['native_report'].strip()
    assert all(proofs['physical']['checks'].values()) and proofs['formal']['strict_native_lec']['passed']
    assert all(proofs['formal']['strict_native_lec']['checks'].values())
    assert len(proofs['function']['initial_runs'])==3
    assert proofs['formal']['function_receipt_sha256']==receipts['function']['sha256']
    gds=Path(proofs['drc']['gds']['path']);assert sha(gds)==proofs['drc']['gds']['sha256']
    from pin_contract import rectangles
    plan=json.loads((folder/'pins.json').read_text());expected,_=rectangles(plan,(folder/'pins.tcl').read_text(),2000)
    received={}
    for line in (gates/('physical-'+macro)/'physical-pins.tsv').read_text().splitlines():
        name,layer,*coords=line.split('\t');assert name not in received
        received[name]=(layer,list(map(int,coords)))
    assert received==expected
    pins=[dict(pin=n,layer=layer,box_dbu=b) for n,(layer,b) in received.items()]
    assert all(p['layer']=='metal10' and p['box_dbu'][2]-p['box_dbu'][0]==4000 and p['box_dbu'][3]-p['box_dbu'][1]==4000 for p in pins)
    (out/'pins.json').write_text(json.dumps(dict(dbu_per_um=2000,pins=pins),indent=2)+'\n')
    files={}
    for original in [results/('6_final.'+s) for s in ('v','sdc','def','odb','spef')]+[gds]:
        target=out/original.name;shutil.copyfile(original,target);assert sha(target)==sha(original)
        files[target.name]=dict(path=str(target),sha256=sha(target),bytes=target.stat().st_size)
    render='''import pya
view=pya.LayoutView()
view.load_layout(INPUT,0)
view.max_hier()
view.add_missing_layers()
view.zoom_fit()
view.save_image(OUTPUT,1600,1600)
'''.replace('INPUT',repr(str(out/'6_final.gds'))).replace('OUTPUT',repr(str(out/'layout.png')))
    (out/'render.py').write_text(render);run(['env','QT_QPA_PLATFORM=offscreen','klayout','-z','-r',out/'render.py'],'render.log')
    assert (out/'layout.png').stat().st_size>1000
    result=dict(passed=True,native_leaf_accepted=True,top=flow['top'],macro=macro.upper(),implementation_count=1,
                die_um=flow['die_um'],native_routing_layers=['metal'+str(i) for i in range(1,11)],
                active_area_um2=proofs['physical']['active_area_um2'],physical_only_area_um2=proofs['physical']['physical_only_area_um2'],
                source_receipt_sha256=sha(folder/'receipt.json'),gate_receipts=receipts,final_files=files,
                pins=dict(path=str(out/'pins.json'),sha256=sha(out/'pins.json'),signal_bits=len(pins)),
                image=dict(path=str(out/'layout.png'),sha256=sha(out/'layout.png')),
                qualified_hard_macro=False,hierarchical_lib_qualified=False,m11_m12_system_qualified=False,
                scope='One actual native M1-M10 final leaf: all-source-matched independent full native/GDS DRC, STA/electrical/RC/PG/pins/connectivity, three-initial-state final simulation and strict all-boundary LEC. Hierarchical timing model and uncalibrated custom metals are separate.')
    if flow.get('postroute_repair'):
        proof=folder/'route-repair-proof.json'
        assert sha(proof)==flow['postroute_repair']['proof_sha256']
        shutil.copyfile(proof,out/proof.name)
        result['postroute_repair_proof']=dict(path=str(out/proof.name),sha256=sha(proof))
    (out/'delivery.json').write_text(json.dumps(result,indent=2)+'\n')


def geometry(delivery,out,run):
    from five_macro_geometry import export
    index=accepted(delivery);macro=index['macro'].lower()
    def selected(root,target,kind):
        assert kind==macro
        proof=accepted(delivery)
        return proof,Path(proof['final_files']['6_final.odb']['path']),dict(delivery_receipt_path=str(delivery/'receipt.json'),
            delivery_receipt_sha256=sha(delivery/'receipt.json'),delivery_report_sha256=sha(delivery/'delivery.json')),proof['pins']['signal_bits'],proof['die_um']
    export(ROOT,out,16,run,macro,selected=selected,technology_name='technology-2um-v1.json',allow_zero_enclosure=True)
