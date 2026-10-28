"""Stdlib-only published continuation invariants; never a physical qualification."""
import csv, gzip, hashlib, io, json, math


def check(out):
    data=out/'data';root=data/'continuation';counts={'act':860,'mxu':2172,'opentpu_aux':2229,'gemm':3753,'vector':2246,'llaccel_aux':13507}
    for case,count in counts.items():
        with gzip.open(data/(case+'_pin_coordinates.csv.gz'),'rt',encoding='utf-8-sig',newline='') as f:
            original={r['pin']:r for r in csv.DictReader(f) if r['plan']=='A'}
        tables=list((root/'inputs'/case).glob('*all_pins.csv.gz'));assert len(tables)==1
        with gzip.open(tables[0],'rt',encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
        proposed={r['pin']:r for r in rows};assert len(rows)==len(proposed)==count and set(original)==set(proposed)
        meta=json.loads((data/(case+'.meta.json')).read_text());unit=meta['units_per_micron'];die=[v/unit for v in meta['die_dbu']]
        for pin,a in original.items():
            b=proposed[pin]
            for k in ['layer','direction','net','use']:assert a[k]==b[k],(case,pin,k)
            for axis in ['x','y']:
                old=float(a[axis+'1_um'])-float(a[axis+'0_um']);new=float(b[axis+'1_um'])-float(b[axis+'0_um'])
                assert abs(old-new)<1e-6,(case,pin,'size')
                i=0 if axis=='x' else 1
                assert die[i]-1e-6<=float(b[axis+'0_um'])<=float(b[axis+'1_um'])<=die[i+2]+1e-6,(case,pin,'bounds')
                assert math.isfinite(float(b[axis+'_um']))
    files=0
    for manifest in (root/'native').glob('*/snapshot.json'):
        for r in json.loads(manifest.read_text())['records']:
            if r['storage']!='LOSSLESS_SNAPSHOT':continue
            p=manifest.parent/r['relative'];content=p.read_bytes();assert hashlib.sha256(content).hexdigest()==r['stored_sha256']
            original=content if r['source'].endswith('.gz') else gzip.decompress(content)
            assert len(original)==r['bytes'] and hashlib.sha256(original).hexdigest()==r['sha256'],r['relative']
            files+=1
    print('PASS_CONTINUATION_PIN_INVARIANTS_AND_NATIVE_SNAPSHOT_HASHES',sum(counts.values()),'pins',files,'files; NOT full physical qualification')
