"""Select seven native macros only from actual accepted fixed-PG deliveries."""
import json,math
from pathlib import Path
from r256_scene import BASE,SCHEMA

REPLACEMENTS={
 'control_c':'control_c_r8','control_route':'control_route_r8',
 'control_s_arbiter':'control_s_arbiter_r7','control_status':'control_status_r8',
 'control_reset_distribution':'control_reset_distribution_r28'}


def select(a,sha):
    assert not a.replacement and not a.addition and not a.s_internal_delivery and not a.pg_deliveries
    a.out.mkdir(parents=True,exist_ok=False);inputs={}
    def bind(p,expected=None):
        p=Path(p);actual=sha(p)
        if expected is not None:assert actual==expected,str(p)
        inputs[str(p)]=actual;return actual
    def read(p,expected=None):bind(p,expected);return json.loads(Path(p).read_text())
    receipt=dict(passed=False,whole_system_qualified=False,inputs=inputs)
    try:
        bind(Path(__file__));bind(Path(__file__).with_name('r256_scene.py'))
        physical=read(a.physical);functions=read(a.functions)
        assert len(physical['leaves'])==len(functions['leaves'])==21
        expected=set(REPLACEMENTS.values())|{'control_adapter_r','r_stream_local'}
        config=read(a.r256_configurations);assert set(config)==expected
        for old in REPLACEMENTS:
            assert old in physical['leaves']and old in functions['leaves']
            del physical['leaves'][old];del functions['leaves'][old]
        for top,path in config.items():
            folder=Path(path);r=read(folder/'receipt.json');assert r['passed']and r['native_leaf_qualified']
            d=read(folder/'delivery.json',r['outputs']['delivery.json'])
            assert d['passed']and d['native_leaf_accepted']and d['top']==top
            assert d['reused_function_and_strict_lec_via_exact_full_view_identity']
            assert d['signal_pin_plan_unchanged']and not d['whole_system_qualified']
            assert set(d['final_files'])=={'6_final.'+v for v in ['v','sdc','def','odb','spef','gds']}
            for entry in d['final_files'].values():bind(entry['path'],entry['sha256'])
            wrapper=read(d['fixed_pg_receipt'],d['fixed_pg_receipt_sha256'])
            assert wrapper['passed']and wrapper['native_drc_zero']and wrapper['full_deck']['total_items']==0
            ph=read(d['fresh_physical_receipt'],d['fresh_physical_receipt_sha256'])
            timing=read(d['fresh_timing_receipt'],d['fresh_timing_receipt_sha256'])
            assert ph['passed']and ph['native_pg_connected']
            assert timing['passed']and timing['timing_passed']and timing['fresh_native_extraction']
            assert all(math.isfinite(timing[k])and timing[k]>=0 and timing[k]==d[k]for k in ['minimum_setup_ns','minimum_hold_ns'])
            assert ph['inputs'][d['fixed_pg_receipt']]==timing['inputs'][d['fixed_pg_receipt']]==d['fixed_pg_receipt_sha256']
            for operation,entry in d['original_gate_receipts'].items():
                g=read(entry['path'],entry['sha256']);assert g['passed']
                name={'physical':'five-macro-physical.json','drc':'five-macro-drc.json','function':'final-function.json','formal':'formal.json'}[operation]
                report=read(Path(entry['path']).parent/name,entry['report_sha256']);assert report['passed']and g['outputs'][name]==entry['report_sha256']
                if operation=='drc':assert report['full_deck']['total_items']==0 and not report['native_report'].strip()
                if operation=='formal':assert all(report['strict_native_lec']['checks'].values())
            assert set(d['original_gate_receipts'])=={'physical','drc','function','formal'}
            proof=d['full_final_netlist'];assert proof['passed'];bind(proof['full_view'],proof['full_view_sha256'])
            for name,digest in proof['input_sha256'].items():bind(name,digest)
            report=folder/'final-function.json';fr=read(report,r['outputs'][report.name]);assert fr['passed']and fr['exact_full_view_identity']and fr['full_final_netlist']==proof
            pins=folder/'pins.json';bind(pins,d['pins_sha256'])
            row=dict(final_files=d['final_files'],pins=str(pins),pins_sha256=d['pins_sha256'],die_um=d['die_um'],fixed_pg_delivery=dict(path=str(folder/'delivery.json'),sha256=sha(folder/'delivery.json'),receipt=str(folder/'receipt.json'),receipt_sha256=sha(folder/'receipt.json')))
            if top=='r_stream_local':
                assert d['placement_phase_um']==[.095,.07]and d['original_native_pin_phase_um']==[0,0]
                row['placement_phase_um']=[.095,.07]
            physical['leaves'][top]=row
            functions['leaves'][top]=dict(receipt=str(folder/'receipt.json'),receipt_sha256=sha(folder/'receipt.json'),report=str(report),report_sha256=sha(report))
        assert set(physical['leaves'])==set(functions['leaves'])==set(BASE.values())|{'control_link8'}
        for data in [physical,functions]:data.update(scene=SCHEMA,selection_inputs=inputs,scope='Exact individually accepted R256 seven-native fixed-PG selection only; all combined geometry/PG/three RC/300MHz/eight actual programs remain required.')
        for name,data in [('physical.json',physical),('functions.json',functions)]:(a.out/name).write_text(json.dumps(data,indent=2)+'\n')
        receipt.update(passed=True,scene=SCHEMA,replacements=REPLACEMENTS,added=['control_adapter_r','r_stream_local'],native_types=23)
    finally:
        receipt['outputs']={p.name:sha(p)for p in a.out.iterdir()if p.is_file()}
        (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
