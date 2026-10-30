"""Stdlib-only published continuation invariants; never a physical qualification."""
import csv, gzip, hashlib, io, json, math


def check(out):
    data=out/'data';root=data/'continuation';counts={'act':860,'mxu':2172,'opentpu_aux':2229,'gemm':3753,'vector':2246,'llaccel_aux':13507}
    actual_pin_checks=0
    for case,count in counts.items():
        with gzip.open(data/(case+'_pin_coordinates.csv.gz'),'rt',encoding='utf-8-sig',newline='') as f:
            original={r['pin']:r for r in csv.DictReader(f) if r['plan']=='A'}
        tables=list((root/'inputs'/case).glob('*all_pins.csv.gz'));assert len(tables)==1
        with gzip.open(tables[0],'rt',encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
        proposed={r['pin']:r for r in rows};assert len(rows)==len(proposed)==count and set(original)==set(proposed)
        assert len({(round(float(r['x_um']),6),round(float(r['y_um']),6),r['layer']) for r in rows})==count,(case,'duplicate same-layer center')
        meta=json.loads((data/(case+'.meta.json')).read_text());unit=meta['units_per_micron'];die=[v/unit for v in meta['die_dbu']]
        for pin,a in original.items():
            b=proposed[pin]
            for k in ['layer','direction','net','use']:assert a[k]==b[k],(case,pin,k)
            if case in ['gemm','vector'] and a.get('known_constant_zero_from_RTL','').lower()=='true':
                assert all(a[k]==b[k] for k in ['x_um','y_um','x0_um','y0_um','x1_um','y1_um']),(case,pin,'constant moved')
            for axis in ['x','y']:
                old=float(a[axis+'1_um'])-float(a[axis+'0_um']);new=float(b[axis+'1_um'])-float(b[axis+'0_um'])
                assert abs(old-new)<1e-6,(case,pin,'size')
                i=0 if axis=='x' else 1
                assert die[i]-1e-6<=float(b[axis+'0_um'])<=float(b[axis+'1_um'])<=die[i+2]+1e-6,(case,pin,'bounds')
                assert math.isfinite(float(b[axis+'_um']))
        revision='act-access-r03' if case=='act' else 'access-r03'
        pin_exports=sorted((root/'native').glob('*/finalized/'+revision+'/'+case+'-C/pins.tsv.gz'))
        if pin_exports:
            with gzip.open(pin_exports[-1],'rt',newline='') as f:actual_rows=[r for r in csv.DictReader(f,delimiter='\t') if r['use'] not in ['POWER','GROUND']]
            physical={r['pin'].replace('\\',''):r for r in actual_rows};assert len(physical)==len(actual_rows)==count and set(physical)==set(proposed)
            for pin,r in physical.items():
                p=proposed[pin]
                for k in ['layer','direction','use']:assert r[k]==p[k],(case,pin,'native',k)
                assert r['net'].replace('\\','')==p['net']
                for k in ['x0','y0','x1','y1']:assert abs(int(r[k])/unit-float(p[k+'_um']))<1e-6,(case,pin,'actual native coordinates')
            actual_pin_checks+=count
    files=0;alternative_pin_checks=0
    for manifest in (root/'native').glob('*/snapshot.json'):
        for r in json.loads(manifest.read_text())['records']:
            if r['storage']!='LOSSLESS_SNAPSHOT':continue
            p=manifest.parent/r['relative'];content=p.read_bytes();assert hashlib.sha256(content).hexdigest()==r['stored_sha256']
            original=content if r['source'].endswith('.gz') else gzip.decompress(content)
            assert len(original)==r['bytes'] and hashlib.sha256(original).hexdigest()==r['sha256'],r['relative']
            files+=1
    for manifest in (root/'terminal_updates').glob('*/index.json'):
        j=json.loads(manifest.read_text());assert not j['full_qualification']
        for r in j['records']:
            content=(manifest.parent/r['relative']).read_bytes();assert hashlib.sha256(content).hexdigest()==r['stored_sha256']
            raw=gzip.decompress(content);assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256']
            files+=1
        if j['case']=='llaccel_aux' and j['revision']=='llsys-pg-r03':
            with gzip.open(root/'inputs/llsys-pg-r03/llaccel_aux_C_pg_r03_all_pins.csv.gz','rt',encoding='utf-8-sig',newline='') as f:expected={r['pin']:r for r in csv.DictReader(f)}
            p=manifest.parent/'finalized/llsys-pg-r03/llaccel_aux-C/pins.tsv.gz'
            with gzip.open(p,'rt',encoding='utf-8-sig',newline='') as f:rows=[r for r in csv.DictReader(f,delimiter='\t') if r['use'] not in ['POWER','GROUND']]
            actual={r['pin'].replace('\\',''):r for r in rows};assert len(actual)==len(rows)==len(expected)==13507
            assert set(actual)==set(expected)
            for pin,r in actual.items():
                e=expected[pin]
                for k in ['layer','direction','use']:assert r[k]==e[k]
                assert r['net'].replace('\\','')==e['net']
                for k in ['x0','y0','x1','y1']:assert abs(int(r[k])/2000-float(e[k+'_um']))<1e-6
            alternative_pin_checks+=len(actual)
    resume_snapshots=0;local_pins=0;eco_model_pins=0
    for manifest in (root/'resume').glob('resume-*/snapshot.json'):
        j=json.loads(manifest.read_text());assert j['full_qualification'] is False
        for r in j['records']:
            if r['storage']!='LOSSLESS_SNAPSHOT':continue
            stored=(manifest.parent/r['relative']).read_bytes();raw=gzip.decompress(stored)
            assert hashlib.sha256(stored).hexdigest()==r['stored_sha256']
            assert len(raw)==r['source_bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256']
            files+=1
        resume_snapshots+=1
    for case,count in [('gemm',3753),('mxu',2172)]:
        exports=sorted((root/'resume').glob('resume-*/eco_views/r02/'+case+'-C/execution.json.gz'))
        if not exports:continue
        p=exports[-1];j=json.loads(gzip.decompress(p.read_bytes()))
        if not j.get('completed_utc'):continue
        assert not j['full_qualification'] and j['native_export_returncode']==0 and j['fresh_model_read_returncode']==0
        assert j['matching_all_signal_model_pins']==count and j['SPEF_replay_matches_source']
        assert j['all_original_signal_and_PG_pins_and_size_exactly_preserved'] and j['pre_RCX_geometry_and_all_sources_unchanged']
        assert j['files']['clean.odb']['sha256']==j['source_geometry_sha256']
        source_revision='r03' if case=='gemm' else 'r04'
        snapshot=p.parents[3]
        with gzip.open(snapshot/'leaf_eco'/source_revision/(case+'-C')/'stages.tsv.gz','rt',newline='') as f:stages={r['stage']:r['status'] for r in csv.DictReader(f,delimiter='\t')}
        assert all(stages.get(s)=='EXECUTED' for s in ['cell_repair','legalization','global_route','detailed_route','VDD','VSS','whole_signal_geometry','rcx','sta'])
        with gzip.open(p.parent/'pins.tsv.gz','rt',newline='') as f:physical=list(csv.DictReader(f,delimiter='\t'))
        expected={r['pin'].replace('\\',''):r['direction'].lower() for r in physical if r['use'] not in ['POWER','GROUND']}
        assert len(expected)==count
        with gzip.open(p.parent/'model_pins.tsv.gz','rt',newline='') as f:model=list(csv.DictReader(f,delimiter='\t'))
        got={r['pin'].split('/')[-1].replace('\\',''):r['direction'].lower() for r in model}
        assert len(got)==len(model) and {k:v for k,v in got.items() if k in expected}==expected
        eco_model_pins+=count
    patch=root/'inputs/ll-local-patch-r01/llaccel_aux_C_local_patch_r01_all_pins.csv.gz'
    if patch.exists():
        with gzip.open(patch,'rt',encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
        proposed={r['pin']:r for r in rows};assert len(proposed)==len(rows)==13507
        with gzip.open(root/'inputs/llsys-pg-r03/llaccel_aux_C_pg_r03_all_pins.csv.gz','rt',encoding='utf-8-sig',newline='') as f:previous={r['pin']:r for r in csv.DictReader(f)}
        assert set(proposed)==set(previous)
        changed=[];die=json.loads((data/'llaccel_aux.meta.json').read_text())['die_dbu']
        assert len({(r['layer'],float(r['x_um']),float(r['y_um'])) for r in rows})==13507
        for pin,b in proposed.items():
            a=previous[pin]
            for key in ['layer','direction','use','net']:assert a[key]==b[key]
            moved=False
            for axis,i in [('x',0),('y',1)]:
                assert abs((float(a[axis+'1_um'])-float(a[axis+'0_um']))-(float(b[axis+'1_um'])-float(b[axis+'0_um'])))<1e-6
                assert die[i]/2000-1e-6<=float(b[axis+'0_um'])<=float(b[axis+'1_um'])<=die[i+2]/2000+1e-6
                moved=moved or abs(float(a[axis+'_um'])-float(b[axis+'_um']))>1e-6
            if moved:changed.append(pin)
        assert set(changed)=={'bit_1382013','bit_6907','bit_1389626'}
        assert sum(r['moved'].lower()=='true' for r in rows)==13184
        local_pins=len(rows)
    print('PASS_CONTINUATION_PIN_INVARIANTS_AND_NATIVE_SNAPSHOT_HASHES',sum(counts.values()),'candidate pins;',actual_pin_checks,'current-access native pins;',alternative_pin_checks,'alternative native pins;',files,'files;',resume_snapshots,'resume snapshots;',local_pins,'proposed local-repair pins;',eco_model_pins,'costed ECO model pins; NOT full physical qualification')
