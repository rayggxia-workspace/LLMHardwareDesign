"""Portable stdlib validation of shipped evidence; never claims physical pass."""
from pathlib import Path
from collections import Counter
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
    total=0
    for c,n in EXPECTED.items():
        data=rows(DATA/f'{c}_pin_coordinates.csv.gz');total+=len(data);assert len(data)==3*n
        plans={p:{r['pin']:r for r in data if r['plan']==p} for p in ['A','B','C']}
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
    for design in ['opentpu','llaccel']:
        s=json.loads(gzip.decompress((DATA/'partition_summary.json.gz').read_bytes()))[design]
        assert s['unassigned_leaves']==0 and len(s['physical_cells'])==3
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
    assert len(list((OUT/'assets').glob('*.png')))==13
    assert len(list((OUT/'assets').glob('*.svg')))==13
    assert all(x not in text for x in ['__PINS__','__PHYSICAL__','__TOTAL__'])
    print('PASS_REPOSITORY_CANDIDATE_EVIDENCE',len(EXPECTED),'blocks',sum(EXPECTED.values()),'original pins',total,'ABC rows',len(index),'file hashes',len(parser.links),'links; NOT physical qualification')
if __name__=='__main__':main()
