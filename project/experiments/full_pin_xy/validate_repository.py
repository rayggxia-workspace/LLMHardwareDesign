"""Portable stdlib validation of shipped evidence; never claims physical pass."""
from pathlib import Path
from collections import Counter,defaultdict
from html.parser import HTMLParser
import csv,gzip,hashlib,json,math,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[2]
OUT=REPO/'docs/experiments/issue-126-full-pin';DATA=OUT/'data'
EXPECTED={'act':860,'mxu':2172,'opentpu_aux':2229,'gemm':3753,'vector':2246,'llaccel_aux':13507}
def rows(p):
    with gzip.open(p,'rt',encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def yes(s):return str(s).lower()=='true'
def read_json(p):return json.loads(gzip.decompress(p.read_bytes()).decode('utf-8') if p.suffix=='.gz' else p.read_text(encoding='utf-8'))
def main():
    gate=json.loads((DATA/'coverage_gate.json').read_text());assert gate['status']=='PASS_ALL_BLOCK_CANDIDATE_COVERAGE_ONLY'
    bindings=rows(DATA/'pin_bindings.csv.gz');assert len(bindings)==24767
    total=0;allplans={}
    for c,n in EXPECTED.items():
        data=rows(DATA/f'{c}_pin_coordinates.csv.gz');total+=len(data);assert len(data)==3*n
        plans={p:{r['pin']:r for r in data if r['plan']==p} for p in ['A','B','C']}
        allplans[c]=plans
        for p in plans:assert len(plans[p])==n
        meta=json.loads((DATA/(c+'.meta.json')).read_text());die=[x/meta['units_per_micron'] for x in meta['die_dbu']]
        ref=plans['A'];assert set(ref)=={r['pin'] for r in bindings if r['case']==c}
        for p,pp in plans.items():
            assert set(pp)==set(ref);xy=set()
            for pin,r in pp.items():
                original=ref[pin]
                for key in ['bus','interface','layer','net','net_id','direction','use']:assert r[key]==original[key],(c,p,pin,key)
                for axis in ['x','y']:
                    width=float(r[axis+'1_um'])-float(r[axis+'0_um']);origwidth=float(original[axis+'1_um'])-float(original[axis+'0_um'])
                    assert abs(width-origwidth)<1e-6,(c,p,pin,'size')
                box=[float(r[k]) for k in ['x0_um','y0_um','x1_um','y1_um']]
                assert box[0]>=die[0]-1e-6 and box[1]>=die[1]-1e-6 and box[2]<=die[2]+1e-6 and box[3]<=die[3]+1e-6
                pair=(r['x_um'],r['y_um']);assert pair not in xy,(c,p,pin,'duplicate');xy.add(pair)
                if c in ['gemm','vector'] and yes(r['known_constant_zero_from_RTL']):
                    assert r['x_um']==original['x_um'] and r['y_um']==original['y_um']
            mm=json.loads((DATA/f'{c}_metrics.json').read_text())[p]
            assert mm['n']==n and mm['layers']==dict(Counter(r['layer'] for r in pp.values()))
        if c in ['act','gemm']:
            old=REPO/'docs/experiments/issue-119-pin-xy/data'/f'{c}_pin_coordinates.csv.gz'
            assert gzip.decompress((DATA/f'{c}_pin_coordinates.csv.gz').read_bytes())==gzip.decompress(old.read_bytes()),'PR120 changed'
        else:
            with gzip.open(DATA/'evidence'/c/'bterms.tsv.gz','rt') as f:
                physical={r['pin'].replace('\\',''):r for r in csv.DictReader(f,delimiter='\t') if r['pin'] not in ['VDD','VSS']}
            assert set(physical)==set(ref)
            for pin,r in ref.items():
                s=physical[pin];assert s['layer']==r['layer'] and s['direction']==r['direction']
                for k in ['x0','y0','x1','y1']:assert abs(float(r[k+'_um'])-int(s[k])/2000)<1e-6
    assert total==74301
    for c in ['mxu','vector','opentpu_aux','llaccel_aux']:
        for r in rows(DATA/f'{c}_pin_coordinates.csv.gz'):
            if r['plan']!='A' and yes(r['moved']):
                for k in ['x0_um','y0_um','x1_um','y1_um']:
                    assert abs(float(r[k])/0.005-round(float(r[k])/0.005))<1e-5,(c,r['pin'],'manufacturing grid')
    physical=list((DATA/'evidence/physical').glob('*/finalized/fullC-r02/act-C/execution.json*'))
    assert physical,'ACT full-C independent physical evidence missing'
    actual=read_json(physical[-1])
    assert actual['independent_DRC_count']==0 and actual['whole_access']['pass'] and actual['clean_byte_identical_to_pre_RCX_source']
    with gzip.open(physical[-1].parent/'pins.tsv.gz','rt') as f:actual_pins={r['pin'].replace('\\',''):r for r in csv.DictReader(f,delimiter='\t') if r['use'] not in ['POWER','GROUND']}
    actrows={r['pin']:r for r in rows(DATA/'act_pin_coordinates.csv.gz') if r['plan']=='C'}
    assert len(actual_pins)==len(actrows)==860
    for pin,r in actrows.items():
        q=actual_pins[pin];assert q['layer']==r['layer'] and q['direction']==r['direction'] and q['use']==r['use'] and q['net'].replace('\\','')==r['net']
        for k in ['x0','y0','x1','y1']:assert abs(int(q[k])/2000-float(r[k+'_um']))<1e-6,(pin,k,'actual full-C XY')
    # Every block's C experiment: full ACT, the exact eight-pin cohort elsewhere.
    for c in EXPECTED:
        rev='fullC-r02' if c=='act' else 'r01' if c=='gemm' else 'grid-r05'
        p=sorted((DATA/'evidence/physical').glob(f'*/finalized/{rev}/{c}-C/execution.json*'))[-1]
        rec=read_json(p);assert rec['export_returncode']==rec['independent_DRC_returncode']==rec['independent_DRC_count']==0
        assert rec['whole_access']['pass'] and rec['source_unchanged'] and rec['clean_byte_identical_to_pre_RCX_source']
        with gzip.open(p.parent/'pins.tsv.gz','rt') as f:pp=[r for r in csv.DictReader(f,delimiter='\t') if r['use'] not in ['POWER','GROUND']]
        assert len(pp)==EXPECTED[c] and len({r['pin'] for r in pp})==EXPECTED[c]
        moved=0
        for r in pp:
            pin=r['pin'].replace('\\','');a=allplans[c]['A'][pin];cc=allplans[c]['C'][pin]
            assert r['layer']==a['layer'] and r['direction']==a['direction'] and r['use']==a['use'] and r['net'].replace('\\','')==a['net']
            aa=[float(a[k+'_um']) for k in ['x0','y0','x1','y1']];bb=[float(cc[k+'_um']) for k in ['x0','y0','x1','y1']];got=[int(r[k])/2000 for k in ['x0','y0','x1','y1']]
            if any(abs(x-y)>1e-6 for x,y in zip(aa,got)):
                moved+=1;assert all(abs(x-y)<1e-6 for x,y in zip(bb,got)),(c,pin,'actual XY differs from proposed C')
        assert moved==(740 if c=='act' else 8),(c,'actual experiment scope')
    for design in ['opentpu','llaccel']:
        s=json.loads(gzip.decompress((DATA/'partition_summary.json.gz').read_bytes()))[design]
        assert s['unassigned_leaves']==0 and len(s['physical_cells'])==3
    # Additional complete original C trials are distinct from eight-pin proofs.
    # Assert exact full pin correspondence even if a physical rule later fails;
    # never turn an expected reported physical failure into a fake "pass".
    for p in (DATA/'evidence/physical').glob('*/finalized/full-other-r01/*-C/execution.json*'):
        rec=read_json(p);c=rec['case']
        with gzip.open(p.parent/'pins.tsv.gz','rt') as f:pp=[r for r in csv.DictReader(f,delimiter='\t') if r['use'] not in ['POWER','GROUND']]
        assert len(pp)==EXPECTED[c] and len({r['pin'] for r in pp})==EXPECTED[c]
        for r in pp:
            want=allplans[c]['C'][r['pin'].replace('\\','')]
            for key in ['layer','direction','use']:assert r[key]==want[key]
            assert r['net'].replace('\\','')==want['net']
            for k in ['x0','y0','x1','y1']:assert abs(int(r[k])/2000-float(want[k+'_um']))<1e-6,(c,r['pin'],'complete C correspondence')
    for c,name,filename,rev,expected_moved in [('gemm','gemm_electrical_r03','gemm_C_electrical_r03_all_pins.csv.gz','electrical-r03',3021),('mxu','mxu_repair_r03','mxu_C_repair_r03_all_pins.csv.gz','mxu-repair-r03',1931)]:
        revision=DATA/'incremental_revisions'/name
        if not revision.exists():continue
        proposed={r['pin']:r for r in rows(revision/filename)}
        assert len(proposed)==EXPECTED[c] and set(proposed)==set(allplans[c]['A'])
        meta=json.loads((DATA/(c+'.meta.json')).read_text());die=[v/meta['units_per_micron'] for v in meta['die_dbu']]
        moved=0;xy=set()
        for pin,r in proposed.items():
            a=allplans[c]['A'][pin]
            for key in ['bus','interface','layer','net','net_id','direction','use']:assert r[key]==a[key],(c,pin,key,'incremental contract')
            point=(r['x_um'],r['y_um']);assert point not in xy;xy.add(point)
            box=[float(r[k+'_um']) for k in ['x0','y0','x1','y1']]
            assert box[0]>=die[0]-1e-6 and box[1]>=die[1]-1e-6 and box[2]<=die[2]+1e-6 and box[3]<=die[3]+1e-6
            if c=='mxu':assert all(abs(v/.005-round(v/.005))<1e-5 for v in box)
            if any(abs(float(r[k+'_um'])-float(a[k+'_um']))>1e-6 for k in ['x0','y0','x1','y1']):moved+=1
            for axis in ['x','y']:assert abs((float(r[axis+'1_um'])-float(r[axis+'0_um']))-(float(a[axis+'1_um'])-float(a[axis+'0_um'])))<1e-6
        assert moved==expected_moved
        p=sorted((DATA/'evidence/physical').glob(f'*/finalized/{rev}/{c}-C/execution.json*'))[-1]
        rec=read_json(p);assert rec['source_unchanged'] and rec['clean_byte_identical_to_pre_RCX_source']
        with gzip.open(p.parent/'pins.tsv.gz','rt') as f:actual=[r for r in csv.DictReader(f,delimiter='\t') if r['use'] not in ['POWER','GROUND']]
        assert len(actual)==EXPECTED[c]
        for r in actual:
            want=proposed[r['pin'].replace('\\','')]
            for key in ['layer','direction','use']:assert r[key]==want[key]
            assert r['net'].replace('\\','')==want['net']
            for k in ['x0','y0','x1','y1']:assert abs(int(r[k])/2000-float(want[k+'_um']))<1e-6,(c,r['pin'],'incremental actual coordinates')
        publication=json.loads((revision/'publication.json').read_text())
        assert hashlib.sha256((revision/(c+'-C.tcl')).read_bytes()).hexdigest()==publication['relocation_Tcl_sha256']
    reject=DATA/'fixed_pg_rejections/llaccel_aux_full_C'
    if reject.exists():
        proof=read_json(reject/'proof.json');assert proof['signal_pins_checked']==13507 and proof['direct_contact_pin_count']==26 and proof['direct_contact_rectangle_pairs']==44
        before=gzip.decompress((reject/'before.pdn.tsv.gz').read_bytes());moved=gzip.decompress((reject/'moved.pdn.tsv.gz').read_bytes())
        assert before==moved and hashlib.sha256(moved).hexdigest()==proof['moved_PG_sha256']==proof['before_PG_sha256']
        actual=gzip.decompress((reject/'moved.pins.tsv.gz').read_bytes());assert hashlib.sha256(actual).hexdigest()==proof['moved_pins_sha256']
        # This SYSTEM wrapper uses scalar bit_N names only; reject any ambiguous
        # Tcl quoting rather than pretending whitespace parsing is general.
        pp=[line.split() for line in actual.decode().splitlines()];assert all(len(r)==9 for r in pp)
        pp=[r for r in pp if r[2] not in ['POWER','GROUND']];assert len(pp)==13507 and len({r[0] for r in pp})==13507
        for r in pp:
            want=allplans['llaccel_aux']['C'][r[0]]
            assert r[1:5]==[want['direction'],want['use'],want['net'],want['layer']]
            for k,v in zip(['x0','y0','x1','y1'],r[5:9]):assert abs(int(v)/2000-float(want[k+'_um']))<1e-6
        for r in proof['contacts']:
            assert r['fixed_PG_net'] in ['VDD','VSS'] and r['layer']==allplans['llaccel_aux']['C'][r['pin']]['layer']
            a=r['actual_pin_box_um'];b=r['PG_shape_box_um'];assert min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])
        stop=read_json(reject/'stop-action.json');assert stop['job']=='92369' and stop['other_jobs_untouched'] and stop['known_direct_short_pins']==26
        if (reject/'checkpoint-index.json').exists():
            checkpoint=read_json(reject/'checkpoint-index.json');assert checkpoint['full_route_completed'] is False and checkpoint['full_physical_qualification'] is False
            assert set(['moved.odb','ripped.odb','global.odb'])<=set(checkpoint['checkpoints'])
            assert all(q['unchanged_during_index'] and len(q['sha256'])==64 and q['bytes']>0 for q in checkpoint['checkpoints'].values())
    controls=DATA/'full_cohort_controls'
    if controls.exists():
        selections=json.loads((controls/'selection.json').read_text())
        for c in EXPECTED:
            chosen={pin for pin,r in allplans[c]['C'].items() if yes(r['moved'])}
            assert chosen==set(selections[c]['pins'])
            assert hashlib.sha256(gzip.decompress((DATA/(c+'_pin_coordinates.csv.gz')).read_bytes())).hexdigest()==selections[c]['candidate_sha256']
            grouped={r['pin']:r['group'] for r in rows(DATA/(c+'_groups.csv.gz')) if r['plan']=='A'}
            optimized=rows(controls/(c+'-Aopt.csv.gz'));assert len(optimized)==len(chosen) and {r['pin'] for r in optimized}==chosen
            before=defaultdict(list);after=defaultdict(list)
            for r in optimized:
                a=allplans[c]['A'][r['pin']]
                for key in ['layer','direction','use','net','bus','interface']:assert r[key]==a[key],(c,r['pin'],key,'Aopt contract')
                k=(grouped[r['pin']],a['original_edge'],a['layer'])
                before[k].append((a['x_um'],a['y_um']));after[k].append((r['x_um'],r['y_um']))
            assert {k:sorted(v) for k,v in before.items()}=={k:sorted(v) for k,v in after.items()},(c,'Aopt source slot set changed')
    for p in (DATA/'evidence/physical').glob('storage_index.json'):
        for original,r in read_json(p).items():
            b=gzip.decompress((p.parent/r['stored_as']).read_bytes());assert len(b)==r['original_bytes'] and hashlib.sha256(b).hexdigest()==r['original_sha256'],original
    models=DATA/'timing_models'
    if models.exists():
        successful=set()
        for summary_path in models.glob('*/summary.json'):
            for item in read_json(summary_path)['records']:
                r=item['actual_receipt']
                if r.get('status')!='NATIVE_EXTRACTED_MODEL_EXPORTED_NOT_QUALIFIED':continue
                c=r['case'];expected={p:a['direction'].lower() for p,a in allplans[c]['A'].items()}
                directory=summary_path.parent/item['model'];lib=gzip.decompress((directory/'timing.lib.gz').read_bytes())
                assert hashlib.sha256(lib).hexdigest()==r['generated_library_sha256']==r['files']['timing.lib']['sha256']
                with gzip.open(directory/'model_pins.tsv.gz','rt') as f:pp=list(csv.DictReader(f,delimiter='\t'))
                actual={q['pin'].split('/')[-1].replace('\\',''):q['direction'].lower() for q in pp};assert len(actual)==len(pp)
                assert {p:d for p,d in actual.items() if p in expected}==expected
                assert set(actual)-set(expected)==set(r['native_bus_aggregate_declarations_not_extra_bits'])|set(r['native_PG_ports_not_signal_pins'])
                assert set(r['native_PG_ports_not_signal_pins'])<=set(['VDD','VSS'])
                for name,q in r['native_bus_aggregate_declarations_not_extra_bits'].items():
                    assert len(q['members'])>1 and all(p in expected and expected[p]==q['actual_native_direction'] for p in q['members'])
                assert r['actual_model_signal_pins']==r['expected_physical_signal_pins']==EXPECTED[c]
                assert r['exact_all_signal_pin_direction_match'] and r['source_odb_and_SPEF_unchanged'] and r['model_has_timing_groups']
                assert all(q['delta_ns'] is not None and abs(q['delta_ns'])<=1e-5 for q in r['SPEF_replay_worst_slack'].values())
                assert r['minimum_period_present']==('minimum_period' in lib.decode())
                assert item['qualified_for_full_system_STA'] is False
                sub=r['source_clean_receipt'].split('/full-pin-20261027/',1)[1]
                matches=list((DATA/'evidence/physical').glob('*/'+sub+'*'));assert matches,(item['model'],'matching clean physical source missing')
                # Multiple immutable publication snapshots are allowed. Every
                # duplicate must still match the exact native source and ODB.
                for match in matches:
                    raw=gzip.decompress(match.read_bytes()) if match.suffix=='.gz' else match.read_bytes()
                    assert hashlib.sha256(raw).hexdigest()==r['source_clean_receipt_sha256']
                    assert json.loads(raw)['clean_odb_sha256']==r['clean_odb_sha256']
                successful.add((c,r['variant']))
        assert all((c,p) in successful for c in EXPECTED for p in ['A','C'])
    semantic=DATA/'rule_semantics/well4-r01'
    if semantic.exists():
        proof=read_json(semantic/'summary.json');assert proof['original_deck_unmodified'] and proof['original_expression_differs_from_width_reference_on_fixtures']
        assert proof['qualified_design_or_rule_deck'] is False and proof['full_original_design_reports_changed'] is False
        examples={r['fixture']:r for r in proof['fixtures']}
        thin=examples['thin_isolated']['counts'];gap=examples['wide_gap150']['counts']
        assert thin.get('ORIGINAL_WELL4',0)==0 and thin['WIDTH200_REFERENCE']>0
        assert gap['ORIGINAL_WELL4']>0 and gap.get('WIDTH200_REFERENCE',0)==gap.get('SPACE135_REFERENCE',0)==0
        for name,r in examples.items():
            assert hashlib.sha256((semantic/(name+'.gds')).read_bytes()).hexdigest()==r['GDS_sha256']
            assert hashlib.sha256(gzip.decompress((semantic/(name+'.lyrdb.gz')).read_bytes())).hexdigest()==r['native_report_sha256']
        for p in (DATA/'rule_semantics').glob('llaccel-A-well-reference-*/summary.json'):
            r=read_json(p);assert r['original_deck_unmodified'] and r['full_qualification'] is False and r['original_full_reports_reclassified_as_pass'] is False
            assert r['installed_original_deck_sha256']==proof['installed_original_deck_sha256']
            assert hashlib.sha256((p.parent/'actual_reference.drc').read_bytes()).hexdigest()==r['reference_runset_sha256']
            assert hashlib.sha256(gzip.decompress((p.parent/'actual_reference.lyrdb.gz').read_bytes())).hexdigest()==r['reference_report_sha256']
    index=json.loads((DATA/'artifact_index.json').read_text())
    for rel,rec in index.items():
        p=OUT/rel;assert p.stat().st_size==rec['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==rec['sha256'],rel
    class Links(HTMLParser):
        def __init__(self):super().__init__();self.links=[]
        def handle_starttag(self,tag,attrs):
            for k,v in attrs:
                if k in ['src','href']:self.links.append(v)
    parser=Links();text=(OUT/'report.html').read_text(encoding='utf-8');parser.feed(text)
    for link in parser.links:
        if link.startswith(('http','#','data:')):continue
        assert (OUT/link.split('#')[0]).exists(),link
    for p in (OUT/'assets').glob('*.svg'):ET.parse(p)
    expected_figures=14
    if (DATA/'continuation/summary.json').exists():
        continuation=read_json(DATA/'continuation/summary.json')
        assert continuation['complete_original_pin_count']==24767 and continuation['candidate_rows_preserved']==74301
        assert not continuation['common_base_frozen'] and not continuation['M11_M12_complete_functions_implemented']
        assert len(continuation['blocks'])==6 and all(not r['full_qualification'] for r in continuation['blocks'])
        from validate_continuation import check as check_continuation
        check_continuation(OUT)
        from validate_gate_matrix import check as check_gate_matrix
        check_gate_matrix(OUT)
        for name in ['research_upper_actual','llsys_pg_revision','common_base_proposed']:
            assert (OUT/'assets'/(name+'.png')).exists() and (OUT/'assets'/(name+'.svg')).exists()
        expected_figures+=3
        if (OUT/'assets/act_parent_landing_actual.png').exists():
            assert (OUT/'assets/act_parent_landing_actual.svg').exists()
            expected_figures+=1
        if (OUT/'data/continuation/resume').exists():
            assert 'id="resume20261028"' in text
            for ext in ['png','svg']:assert (OUT/'assets'/('llsys_local_repair_attempt.'+ext)).exists()
            expected_figures+=1
    if (OUT/'assets/equal_cost_leaf_margins.png').exists():
        assert (OUT/'assets/equal_cost_leaf_margins.svg').exists()
        expected_figures+=1
    if (OUT/'assets/common_placement_actual.png').exists():
        assert (OUT/'assets/common_placement_actual.svg').exists()
        expected_figures+=1
    if (OUT/'assets/mxu_M6_actual_ownership.png').exists():
        assert (OUT/'assets/mxu_M6_actual_ownership.svg').exists()
        expected_figures+=1
    if (OUT/'assets/actual_critical_path_diagnosis.png').exists():
        assert (OUT/'assets/actual_critical_path_diagnosis.svg').exists()
        expected_figures+=1
    if (OUT/'assets/common_shared_conductors_actual.png').exists():
        assert (OUT/'assets/common_shared_conductors_actual.svg').exists()
        expected_figures+=1
    if (OUT/'assets/gemm_real_diode_access.png').exists():
        assert (OUT/'assets/gemm_real_diode_access.svg').exists()
        assert 'assets/gemm_real_diode_access.png' in text and 'assets/gemm_real_diode_access.svg' in text
        expected_figures+=1
    if (OUT/'assets/system_actual_M2_conflict.png').exists():
        assert (OUT/'assets/system_actual_M2_conflict.svg').exists()
        assert 'assets/system_actual_M2_conflict.png' in text and 'assets/system_actual_M2_conflict.svg' in text
        expected_figures+=1
    if (OUT/'assets/mxu_actual_M6_escape_context.png').exists():
        assert (OUT/'assets/mxu_actual_M6_escape_context.svg').exists()
        assert 'assets/mxu_actual_M6_escape_context.png' in text and 'assets/mxu_actual_M6_escape_context.svg' in text
        expected_figures+=1
    assert len(list((OUT/'assets').glob('*.png')))==expected_figures
    assert len(list((OUT/'assets').glob('*.svg')))==expected_figures
    assert all(x not in text for x in ['__PINS__','__PHYSICAL__','__TOTAL__'])
    print('PASS_REPOSITORY_CANDIDATE_EVIDENCE',len(EXPECTED),'blocks',sum(EXPECTED.values()),'original pins',total,'ABC rows',len(index),'file hashes',len(parser.links),'links; NOT physical qualification')
if __name__=='__main__':main()
