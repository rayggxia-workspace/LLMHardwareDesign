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
    physical=list((DATA/'evidence/physical').glob('*/finalized/fullC-r02/act-C/execution.json'))
    assert physical,'ACT full-C independent physical evidence missing'
    actual=json.loads(physical[-1].read_text())
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
        p=sorted((DATA/'evidence/physical').glob(f'*/finalized/{rev}/{c}-C/execution.json'))[-1]
        rec=json.loads(p.read_text());assert rec['export_returncode']==rec['independent_DRC_returncode']==rec['independent_DRC_count']==0
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
    assert len(list((OUT/'assets').glob('*.png')))==14
    assert len(list((OUT/'assets').glob('*.svg')))==14
    assert all(x not in text for x in ['__PINS__','__PHYSICAL__','__TOTAL__'])
    print('PASS_REPOSITORY_CANDIDATE_EVIDENCE',len(EXPECTED),'blocks',sum(EXPECTED.values()),'original pins',total,'ABC rows',len(index),'file hashes',len(parser.links),'links; NOT physical qualification')
if __name__=='__main__':main()
