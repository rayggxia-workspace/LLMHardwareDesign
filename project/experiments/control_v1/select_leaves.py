"""Bind reused qualified leaves and newly qualified replacements without copying qualification."""
import argparse,hashlib,json,re
from pathlib import Path

REPLACEABLE={'control_c','control_endpoint_queue','control_d','control_axil_bridge',
    'control_adapter_m','control_adapter_n','control_adapter_e','control_adapter_g','control_adapter_s','control_adapter_t',
    'control_route','control_s_arbiter','control_status','control_reset_distribution'}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--physical',type=Path,required=True)
    p.add_argument('--functions',type=Path,required=True)
    p.add_argument('--replacement',type=Path,action='append')
    p.add_argument('--s-internal-delivery',type=Path,help='Explicit user-authorized S physical replacement, freshly qualified by all four gates')
    p.add_argument('--addition',type=Path,action='append',
                   help='Independently qualified control_link8 only; preserves every existing leaf')
    p.add_argument('--pg-deliveries',type=Path)
    p.add_argument('--r256-configurations',type=Path,help='Exact seven independently accepted fixed-PG R256 configurations; replace five control types and add R plus its adapter')
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.r256_configurations:
        from r256_selection import select
        select(a,sha);return
    if a.pg_deliveries:
        assert not a.replacement and not a.addition and not a.s_internal_delivery
        from pg_selection import select
        select(a,sha);return
    assert a.replacement or a.addition or a.s_internal_delivery
    a.out.mkdir(parents=True,exist_ok=False)
    physical=json.loads(a.physical.read_text());functions=json.loads(a.functions.read_text())
    original_count=len(physical['leaves']);assert original_count in (19,20,21)
    bindings={str(a.physical):sha(a.physical),str(a.functions):sha(a.functions),str(Path(__file__)):sha(Path(__file__))}
    replacements=[]
    additions=[]
    for folder in (a.replacement or [])+(a.addition or [])+([a.s_internal_delivery]if a.s_internal_delivery else[]):
        receipt=json.loads((folder/'receipt.json').read_text());assert receipt['passed']
        path=folder/'delivery.json';assert sha(path)==receipt['outputs']['delivery.json']
        delivery=json.loads(path.read_text());assert delivery['passed'] and delivery['native_leaf_accepted']
        top=delivery['top']
        if folder in (a.addition or []):
            assert top=='control_link8' and top not in physical['leaves']
            additions.append(top)
        elif folder==a.s_internal_delivery:
            assert top=='block_feed_s_macro' and top in physical['leaves']
            proof=delivery['S_internal_drive']
            assert proof['owner']=='block_feed_s_macro M1-M10' and proof['all_four_gates_fresh']
            assert proof['no_new_registers'] and proof['no_latency_or_protocol_change']
            drive=proof['actual_final_driver_proof']
            assert drive['passed'] and drive['output_count']==788 and drive['all_actual_drivers_BUF_X32']
            assert sha(drive['table'])==drive['table_sha256']
            bindings[drive['table']]=drive['table_sha256']
            raw=Path(proof['raw_producer'])/'receipt.json';assert sha(raw)==proof['raw_producer_receipt_sha256']
            bindings[str(raw)]=sha(raw)
        else:assert top in REPLACEABLE
        assert top not in replacements;replacements.append(top)
        bindings[str(folder/'receipt.json')]=sha(folder/'receipt.json');bindings[str(path)]=sha(path)
        for operation,row in delivery['gate_receipts'].items():
            gate=Path(row['path']);assert sha(gate)==row['sha256']
            proof=json.loads(gate.read_text());assert proof['passed'] and proof['operation']==operation
            bindings[str(gate)]=sha(gate)
            report_name={'physical':'five-macro-physical.json','drc':'five-macro-drc.json','function':'final-function.json','formal':'formal.json'}[operation]
            report=gate.parent/report_name;assert sha(report)==row['report_sha256']==proof['outputs'][report_name]
            result=json.loads(report.read_text());assert result['passed']
            assert result['source_receipt_sha256']==delivery['source_receipt_sha256']
        assert set(delivery['gate_receipts'])=={'physical','drc','function','formal'}
        assert set(delivery['final_files'])=={'6_final.'+s for s in ('v','sdc','def','odb','spef','gds')}
        for row in delivery['final_files'].values():assert sha(row['path'])==row['sha256']
        pins=folder/'pins.json';assert sha(pins)==delivery['pins_sha256']
        text=Path(delivery['final_files']['6_final.def']['path']).read_text()
        units=re.search(r'UNITS DISTANCE MICRONS (\d+) ;',text);assert units
        die=re.search(r'DIEAREA \( (\d+) (\d+) \) \( (\d+) (\d+) \) ;',text);assert die
        x0,y0,x1,y1=map(int,die.groups());assert x0==y0==0
        dimensions=[x1/int(units[1]),y1/int(units[1])];assert dimensions==delivery['die_um']
        physical['leaves'][top]=dict(pins=str(pins),pins_sha256=sha(pins),final_files=delivery['final_files'],die_um=dimensions,
            selection_delivery=dict(path=str(path),sha256=sha(path),receipt=str(folder/'receipt.json'),receipt_sha256=sha(folder/'receipt.json')))
        if folder==a.s_internal_delivery:physical['leaves'][top]['S_internal_drive']=delivery['S_internal_drive']
        row=delivery['gate_receipts']['function'];report=Path(row['path']).parent/'final-function.json'
        assert sha(report)==row['report_sha256']
        functions['leaves'][top]=dict(receipt=row['path'],receipt_sha256=row['sha256'],report=str(report),report_sha256=sha(report))
    if original_count==19:
        assert {'control_axil_bridge','control_s_arbiter','control_reset_distribution'}<=set(replacements)
    else:
        allowed=REPLACEABLE|({'block_feed_s_macro'}if a.s_internal_delivery else set())
        assert set(replacements)-set(additions)<=allowed and 'control_reset_distribution' in physical['leaves']
    assert len(physical['leaves'])==len(functions['leaves'])==max(20,original_count)+len(additions)
    physical['selection_inputs']=functions['selection_inputs']=bindings
    physical['scope']='Selected individually qualified native leaves; no composed-system qualification.'
    functions['scope']='Selected actual complete physical-functional views; no composed-system qualification.'
    for name,data in [('physical.json',physical),('functions.json',functions)]:
        (a.out/name).write_text(json.dumps(data,indent=2)+'\n')
    (a.out/'receipt.json').write_text(json.dumps(dict(passed=True,inputs=bindings,replacements=[t for t in replacements if t not in additions],additions=additions,leaves=len(physical['leaves']),
        outputs={name:sha(a.out/name) for name in ('physical.json','functions.json')},whole_system_qualified=False),indent=2)+'\n')

if __name__=='__main__':main()
