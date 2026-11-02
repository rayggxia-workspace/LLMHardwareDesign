"""Deliver fixed PG leaves only after fresh physical/timing and exact logic identity."""
import json,shutil,sys
from pathlib import Path


def deliver(a,row,wrapper_receipt,bind,run,sha):
    root=Path(__file__).resolve().parents[3]
    native=root/'project/experiments/block_v1';sys.path.insert(0,str(native))
    from native_signal_view import export
    for name in ('native_signal_view.py','native_logic_projection.py','structural_view.py','io_slots.py'):
        bind(native/name)
    # Retained T has an indexed delivery directory separate from raw final
    # files, and names its function gate "final-function". Verify that exact
    # historical schema rather than guessing receipts beside the netlist.
    retained_t=a.leaf=='transaction6k' and 'bundle' in row
    if retained_t:
        bundle=row['bundle'];assert bundle['passed'] and bundle['native_leaf_accepted'] and bundle['macro']=='T'
        original=Path(bundle['original_delivery']);delivery_name='five-macro-delivery.json'
        assert bundle['final_files']==row['final_files']
    else:
        original=Path(row['final_files']['6_final.v']['path']).parent;delivery_name='delivery.json'
    for name in ('receipt.json',delivery_name):bind(original/name)
    original_receipt=json.loads((original/'receipt.json').read_text())
    old=json.loads((original/delivery_name).read_text())
    assert original_receipt['passed'] and old['passed'] and old['native_leaf_accepted']
    assert sha(original/delivery_name)==original_receipt['outputs'][delivery_name]
    assert old['top']==a.leaf and old['final_files']==row['final_files']
    if retained_t:assert old['source_receipt_sha256']==bundle['source_receipt_sha256']
    old=dict(old,gate_receipts={('function' if op=='final-function' else op):entry for op,entry in old['gate_receipts'].items()})
    for entry in old['final_files'].values():bind(entry['path'],entry['sha256'])
    reports={}
    for op,entry in old['gate_receipts'].items():
        path=Path(entry['path']);bind(path,entry['sha256']);receipt=json.loads(path.read_text());assert receipt['passed']
        filename=Path(entry['report_path']).name if 'report_path' in entry else {'physical':'five-macro-physical.json','drc':'five-macro-drc.json','function':'final-function.json','formal':'formal.json'}[op]
        path=Path(entry.get('report_path',str(path.parent/filename)))
        bind(path,entry['report_sha256']);assert sha(path)==receipt['outputs'][filename]
        report=json.loads(path.read_text());assert report['passed']
        assert report['source_receipt_sha256']==old['source_receipt_sha256']
        reports[op]=report
    assert set(reports)=={'physical','drc','function','formal'}
    assert all(reports['physical']['checks'].values())
    assert reports['drc']['full_deck']['total_items']==0 and not reports['drc']['native_report'].strip()
    assert all(reports['formal']['strict_native_lec']['checks'].values())
    oldview=reports['function']['full_final_netlist'];assert oldview['passed']
    bind(oldview['full_view'],oldview['full_view_sha256'])
    for path,digest in oldview['input_sha256'].items():bind(path,digest)
    for path in (a.physical_check,a.timing_check):
        bind(path/'receipt.json');receipt=json.loads((path/'receipt.json').read_text());assert receipt['passed']
        assert receipt['inputs'][str(a.wrapper/'receipt.json')]==sha(a.wrapper/'receipt.json')
        for name,digest in receipt['outputs'].items():bind(path/name,digest)
    physical=json.loads((a.physical_check/'receipt.json').read_text())
    timing=json.loads((a.timing_check/'receipt.json').read_text())
    assert physical['native_pg_connected'] and timing['fresh_native_extraction'] and timing['timing_passed']
    # Give the exporter a locally explicit actual-input index, not a fabricated
    # acceptance receipt. Its independent ODB-to-Verilog and Yosys comparison
    # still executes on the new wrapper, including every protection cell.
    inputs=a.out/'physical-source';inputs.mkdir()
    for name,path in [('6_final.odb',a.wrapper/'wrapper.odb'),('6_final.v',Path(row['final_files']['6_final.v']['path']))]:
        (inputs/name).symlink_to(path)
    binding={'outputs':{str(p.relative_to(a.out)):sha(p) for p in inputs.iterdir()}}
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib');bind(lib)
    actual,proof=export(root,a.out,run,a.out,binding,inputs,a.leaf,lib)
    assert sha(actual)==oldview['full_view_sha256'],'New actual complete signal view differs from accepted function/LEC view'
    function=dict(passed=True,top=a.leaf,full_final_netlist=proof,
                  original_function_gate=old['gate_receipts']['function'],
                  original_strict_formal_gate=old['gate_receipts']['formal'],
                  exact_full_view_identity=True,
                  scope='Actual new ODB export byte-identical to the complete input of the original qualified final function and strict native LEC gates; no new simulated result invented.')
    (a.out/'final-function.json').write_text(json.dumps(function,indent=2)+'\n')
    sources={name:Path(entry['path']) for name,entry in row['final_files'].items()}
    sources.update({'6_final.odb':a.wrapper/'wrapper.odb','6_final.def':a.wrapper/'wrapper.def',
                    '6_final.gds':a.wrapper/'wrapper.gds','6_final.spef':a.timing_check/'6_final.spef',
                    '6_final.sdc':a.timing_check/'6_final.sdc'})
    files={}
    for name,path in sources.items():
        bind(path);target=a.out/name;shutil.copyfile(path,target);assert sha(target)==sha(path)
        files[name]=dict(path=str(target),sha256=sha(target),bytes=target.stat().st_size)
    bind(row['pins'],row['pins_sha256']);shutil.copyfile(row['pins'],a.out/'pins.json')
    text='import pya\nv=pya.LayoutView()\nv.load_layout('+repr(str(a.out/'6_final.gds'))+',0)\nv.max_hier()\nv.add_missing_layers()\nv.zoom_fit()\nv.save_image('+repr(str(a.out/'layout.png'))+',1600,1600)\n'
    (a.out/'render.py').write_text(text);run(['env','QT_QPA_PLATFORM=offscreen','klayout','-z','-r',a.out/'render.py'],'render.log')
    assert (a.out/'layout.png').stat().st_size>1000
    delivery=dict(passed=True,native_leaf_accepted=True,top=a.leaf,final_files=files,
        original_delivery=str(original/delivery_name),original_delivery_sha256=sha(original/delivery_name),
        original_source_receipt_sha256=old['source_receipt_sha256'],
        original_gate_receipts=old['gate_receipts'],full_final_netlist=proof,
        reused_function_and_strict_lec_via_exact_full_view_identity=True,
        fixed_pg_receipt=str(a.wrapper/'receipt.json'),fixed_pg_receipt_sha256=sha(a.wrapper/'receipt.json'),
        fresh_physical_receipt=str(a.physical_check/'receipt.json'),fresh_physical_receipt_sha256=sha(a.physical_check/'receipt.json'),
        fresh_timing_receipt=str(a.timing_check/'receipt.json'),fresh_timing_receipt_sha256=sha(a.timing_check/'receipt.json'),
        minimum_setup_ns=timing['minimum_setup_ns'],minimum_hold_ns=timing['minimum_hold_ns'],
        die_um=old['die_um'],active_area_um2=old['active_area_um2'],
        image_sha256=sha(a.out/'layout.png'),pins_sha256=sha(a.out/'pins.json'),
        signal_pin_plan_unchanged=True,pg_access_odb=str(a.wrapper/'wrapper.odb'),
        whole_system_qualified=False,m11_m12_system_qualified=False,
        scope='Actual fixed M1-M10 PG leaf: fresh full native/GDS DRC, fresh RC/STA and PG continuity. Actual complete ODB signal view byte-identical to original qualified final function/strict LEC input. No whole-system qualification.')
    (a.out/'delivery.json').write_text(json.dumps(delivery,indent=2)+'\n')
    return delivery
