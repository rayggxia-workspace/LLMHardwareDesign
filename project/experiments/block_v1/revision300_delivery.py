"""Same-source final files and native geometry, with no old acceptance transfer."""
import json
from pathlib import Path


def config(root):
    p=root/'project/experiments/block_v1/revision300-deliveries.json'
    d=json.loads(p.read_text());assert d['schema']=='revision300-deliveries/1'
    return d


def signal_geometry(root, out, kind, source_receipt_sha256, flow):
    """The revised V/R need actual whole routed connectivity."""
    from io_slots import file_sha
    d = config(root)
    relative = d.get('signal_geometry', {}).get(kind)
    if kind in ('v','r'):
        assert relative, 'Current revised V/R require whole routed signal proof'
    if relative is None:
        return None
    folder = out.parents[2]/relative
    assert out.parents[2] in folder.resolve().parents
    receipt = json.loads((folder/'receipt.json').read_text())
    assert receipt['passed'] and receipt['mode'] == folder.name
    path = folder/'revision300-signal-connectivity.json'
    assert file_sha(path) == receipt['outputs'][path.name]
    proof = json.loads(path.read_text())
    assert proof['passed'] and proof['original_inputs_unchanged']
    assert proof['source_receipt_sha256'] == source_receipt_sha256
    assert proof['actual_input_sha256'] == {
        name: flow['final_files'][name]['sha256'] for name in ('6_final.odb', '6_final.def')}
    connected = proof['connectivity']
    assert connected['passed'] and connected['exact_all_normal_def_net_coverage']
    assert connected['exact_first_def_odb_name_mapping'] and not connected['failures']
    totals = connected['totals']
    assert totals['nets'] > 0 and totals['passed'] == totals['nets'] and not totals.get('failed', 0)
    assert totals['terminals'] > 0 and totals['shapes'] > 0 and not totals['empty_no_terminals']
    return dict(receipt_path=str(folder/'receipt.json'), receipt_sha256=file_sha(folder/'receipt.json'),
                report_path=str(path), report_sha256=file_sha(path), source_receipt_sha256=source_receipt_sha256)


def deliver(root,out,cpus,run,kind):
    from five_macro_delivery import final_leaf
    from revision300_receive import source
    d=config(root);base=out.parents[2]
    gates=base/d['gates'][kind]
    assert gates.name=='tasks' and base in gates.resolve().parents
    if kind in ('v','r'):
        from io_slots import file_sha
        native, _, flow, _ = source(root, out, kind)
        signal_geometry(root, out, kind, file_sha(native/'receipt.json'), flow)
    final_leaf(root,out,cpus,run,kind,
               gate_roots={stage:gates for stage in ('physical','drc','final-function','formal')},
               selected=lambda target,macro:source(root,target,macro),gate_prefix='revision300-',pin_size_um=2.)


def accepted(root,out,kind):
    from io_slots import file_sha
    from revision300_receive import source
    d=config(root);base=out.parents[2];folder=base/d['delivery'][kind]
    assert base in folder.resolve().parents and folder.name=='revision300-delivery-'+kind
    r=json.loads((folder/'receipt.json').read_text());assert r['passed'] and r['mode']==folder.name
    p=folder/'five-macro-delivery.json';assert file_sha(p)==r['outputs'][p.name]
    index=json.loads(p.read_text());assert index['passed'] and index['native_leaf_accepted'] and index['implementation_count']==1
    native,_,flow,_=source(root,out,kind)
    assert index['source_receipt_sha256']==file_sha(native/'receipt.json')
    assert set(index['gate_receipts'])=={'physical','drc','final-function','formal'}
    for gate in index['gate_receipts'].values():
        rp=Path(gate['path']);proof=Path(gate['report_path'])
        assert base in rp.resolve().parents and rp.parent==proof.parent
        assert file_sha(rp)==gate['sha256'] and file_sha(proof)==gate['report_sha256']
        receipt=json.loads(rp.read_text());bound=json.loads(proof.read_text())
        assert receipt['passed'] and bound['passed'] and receipt['outputs'][proof.name]==file_sha(proof)
        assert bound['source_receipt_sha256']==index['source_receipt_sha256']
    for key,row in index['final_files'].items():
        f=Path(row['path']);assert base in f.resolve().parents and f.stat().st_size==row['bytes'] and file_sha(f)==row['sha256']
    assert flow['die_um']==index['die_um']
    provenance = dict(delivery_receipt_path=str(folder/'receipt.json'),
        delivery_receipt_sha256=file_sha(folder/'receipt.json'),delivery_report_sha256=file_sha(p))
    connected = signal_geometry(root, out, kind, index['source_receipt_sha256'], flow)
    if connected is not None:
        provenance['whole_signal_geometry'] = connected
    return index,Path(index['final_files']['6_final.odb']['path']),provenance,index['pins']['signal_bits'],index['die_um']


def geometry(root,out,cpus,run,kind):
    from five_macro_geometry import export
    export(root,out,cpus,run,kind,selected=accepted,technology_name='technology-2um-v1.json',allow_zero_enclosure=True)
