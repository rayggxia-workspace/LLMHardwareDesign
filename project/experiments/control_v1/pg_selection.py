"""Build source-bound manifests from individually accepted fixed-PG deliveries."""
import json
from pathlib import Path


def select(a,sha):
    a.out.mkdir(parents=True,exist_ok=False)
    physical=json.loads(a.physical.read_text());functions=json.loads(a.functions.read_text())
    inputs={str(a.physical):sha(a.physical),str(a.functions):sha(a.functions),str(Path(__file__)):sha(Path(__file__))}
    leaves={};views={}
    for top,row in physical['leaves'].items():
        folder=a.pg_deliveries/top;receipt_path=folder/'receipt.json';path=folder/'delivery.json'
        receipt=json.loads(receipt_path.read_text());assert receipt['passed'] and receipt['native_leaf_qualified']
        assert sha(path)==receipt['outputs']['delivery.json']
        delivery=json.loads(path.read_text());assert delivery['passed'] and delivery['native_leaf_accepted'] and delivery['top']==top
        for file in (receipt_path,path):inputs[str(file)]=sha(file)
        for name,entry in delivery['final_files'].items():
            assert name in {'6_final.'+suffix for suffix in ('v','sdc','def','odb','spef','gds')}
            assert sha(entry['path'])==entry['sha256'];inputs[entry['path']]=entry['sha256']
        assert len(delivery['final_files'])==6
        previous=functions['leaves'][row.get('bundle',{}).get('macro',top)]
        for key in ('receipt','report'):
            assert sha(previous[key])==previous[key+'_sha256'];inputs[previous[key]]=previous[key+'_sha256']
        previous_receipt=json.loads(Path(previous['receipt']).read_text());assert previous_receipt['passed']
        assert previous_receipt['outputs'][Path(previous['report']).name]==previous['report_sha256']
        old=json.loads(Path(previous['report']).read_text());assert old['passed']
        proof=delivery['full_final_netlist'];assert proof['passed']
        assert proof['full_view_sha256']==old['full_final_netlist']['full_view_sha256']==sha(proof['full_view'])
        assert delivery['reused_function_and_strict_lec_via_exact_full_view_identity']
        for name,digest in proof['input_sha256'].items():assert sha(name)==digest;inputs[name]=digest
        assert delivery['pins_sha256']==row['pins_sha256']==sha(folder/'pins.json')
        report=a.out/(top+'-function.json')
        report.write_text(json.dumps(dict(passed=True,full_final_netlist=proof,
            fixed_pg_delivery=str(path),fixed_pg_delivery_sha256=sha(path),
            original_function=previous,exact_complete_physical_view_identity=True,
            whole_system_qualified=False),indent=2)+'\n')
        gate=a.out/(top+'-function-receipt.json')
        gate.write_text(json.dumps(dict(passed=True,inputs={str(receipt_path):sha(receipt_path),str(path):sha(path),**{previous[k]:previous[k+'_sha256'] for k in ('receipt','report')}},
            outputs={report.name:sha(report)},scope='Exact complete signal-view identity transfer only; source function/strict LEC retained, no newly simulated result.'),indent=2)+'\n')
        views[top]=dict(receipt=str(gate),receipt_sha256=sha(gate),report=str(report),report_sha256=sha(report))
        leaves[top]=dict(final_files=delivery['final_files'],pins=row['pins'],pins_sha256=row['pins_sha256'],die_um=delivery['die_um'],
            fixed_pg_delivery=dict(path=str(path),sha256=sha(path),receipt=str(receipt_path),receipt_sha256=sha(receipt_path)))
        if 'S_internal_drive' in row:
            assert top=='block_feed_s_macro' and delivery['S_internal_drive']==row['S_internal_drive']
            leaves[top]['S_internal_drive']=row['S_internal_drive']
    assert len(leaves)==len(views)==len(physical['leaves'])and len(leaves)in(20,21)
    if len(leaves)==21:assert 'control_link8'in leaves
    scope='Selected individually accepted actual fixed-PG M1-M10 leaves. Whole geometry, upper RC/STA and system qualification remain separate.'
    for name,data in [('physical.json',dict(leaves=leaves,selection_inputs=inputs,scope=scope)),('functions.json',dict(leaves=views,selection_inputs=inputs,scope=scope))]:
        (a.out/name).write_text(json.dumps(data,indent=2)+'\n')
    (a.out/'receipt.json').write_text(json.dumps(dict(passed=True,inputs=inputs,whole_system_qualified=False,
        outputs={p.name:sha(p) for p in a.out.iterdir() if p.is_file()}),indent=2)+'\n')
