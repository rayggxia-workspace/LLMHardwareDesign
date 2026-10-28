"""Standard-library validation of the published inventory/evidence; never a DRC check."""
from pathlib import Path
from collections import Counter
from html.parser import HTMLParser
import csv,gzip,hashlib,json,re

REPO=Path(__file__).resolve().parents[3]
DOC=REPO/'docs/experiments/issue-119-pin-xy'
DATA=DOC/'data'

def read_csv(name):
    with gzip.open(DATA/(name+'.gz'),'rt',encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def truth(s):return str(s).lower()=='true'
def check_links(path):
    s=path.read_text(encoding='utf-8');targets=[]
    if path.suffix=='.md':targets=re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',s)
    else:
        class P(HTMLParser):
            def handle_starttag(self,t,a):
                d=dict(a)
                if t=='a' and d.get('href'):targets.append(d['href'])
                if t=='img' and d.get('src'):targets.append(d['src'])
        P().feed(s)
    for t in targets:
        if t.startswith(('http:','https:','data:','#')):continue
        p=(path.parent/t.split('#')[0]).resolve();assert p.is_file(),(path,t)
        assert REPO in p.parents,(path,t,'outside repository')
    return len(targets)

def main():
    original=json.loads(gzip.decompress((DATA/'source_pin_data.json.gz').read_bytes()))
    refs=[dict(zip(original['columns'],r)) for r in original['rows']]
    rows=read_csv('all_pin_coordinates.csv');assert len(rows)==13839
    keys={(r['case'],r['plan'],r['pin']) for r in rows};assert len(keys)==len(rows)
    metrics=json.loads((DATA/'metrics.json').read_text(encoding='utf-8'))
    for case,n in [('act',860),('gemm',3753)]:
        ref={r['pin']:r for r in refs if r['case']==case and r['use'] not in ['POWER','GROUND']};assert len(ref)==n
        baseline={r['pin']:r for r in rows if r['case']==case and r['plan']=='A'}
        percase=read_csv(case+'_pin_coordinates.csv');assert percase==[r for r in rows if r['case']==case]
        meta=json.loads((DATA/(case+'.meta.json')).read_text(encoding='utf-8'));units=meta['units_per_micron']
        w,h=[v/units for v in meta['die_dbu'][2:]];macros=[[v/units for v in m['bbox_dbu']] for m in meta['macros']]
        for plan in 'ABC':
            part=[r for r in percase if r['plan']==plan];assert len(part)==n and set(r['pin'] for r in part)==set(ref)
            assert len({(r['x_um'],r['y_um']) for r in part})==n
            for r in part:
                p=r['pin'];s=ref[p];a=baseline[p]
                for c in ['bus','interface','direction','use','layer']:assert r[c]==s[c],(case,plan,p,c)
                for c in ['net','net_id','target_layer','external_target']:assert r[c]==a[c]
                x0,y0,x1,y1=[float(r[k]) for k in ['x0_um','y0_um','x1_um','y1_um']]
                assert 0<=x0<=x1<=w+1e-6 and 0<=y0<=y1<=h+1e-6
                assert abs((x1-x0)-(float(s['x1_um'])-float(s['x0_um'])))<1e-6
                assert abs((y1-y0)-(float(s['y1_um'])-float(s['y0_um'])))<1e-6
                assert not any(x0<m[2] and x1>m[0] and y0<m[3] and y1>m[1] for m in macros)
                moved=abs(float(r['x_um'])-float(a['x_um']))+abs(float(r['y_um'])-float(a['y_um']))>1e-6
                assert moved==truth(r['moved'])
                if truth(r['known_constant_zero_from_RTL']):assert not moved
                if plan=='A':
                    for c in ['x_um','y_um','x0_um','y0_um','x1_um','y1_um']:assert abs(float(r[c])-float(s[c]))<1e-6
            m=metrics[case][plan];assert m['n']==n and m['moved']==sum(truth(r['moved']) for r in part)
            assert dict(Counter(r['layer'] for r in part))==m['layers']
            if case=='gemm':assert sum(truth(r['known_constant_zero_from_RTL']) for r in part)==288
        groups=read_csv(case+'_groups.csv');assert len(groups)==3*n
        for plan in 'ABC':
            gg={r['pin']:r['group'] for r in groups if r['plan']==plan};assert set(gg)==set(ref)
            for k in range(4 if case=='act' else 64):
                data='w_data' if case=='act' else 'gemm_wr_wdata';strobe='we' if case=='act' else 'gemm_wr_wstrb'
                bundle={gg[f'{data}[{8*k+j}]'] for j in range(8)}|{gg[f'{strobe}[{k}]']};assert len(bundle)==1
        pg=read_csv(case+'_pg_coordinates.csv')
        pgref=[r for r in refs if r['case']==case and r['use'] in ['POWER','GROUND']]
        for plan in 'ABC':
            part=[r for r in pg if r['plan']==plan];assert len(part)==len(pgref)
            for r,s in zip(part,pgref):
                for c in ['pin','layer','direction','use']:assert r[c]==s[c]
                for c in ['x_um','y_um','x0_um','y0_um','x1_um','y1_um']:assert abs(float(r[c])-float(s[c]))<1e-6
    manifest=json.loads((DATA/'manifest.json').read_text(encoding='utf-8'))
    for r in manifest['files']:
        p=REPO/r['path'];raw=p.read_bytes();assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256'],r['path']
        if 'decompressed_sha256' in r:assert hashlib.sha256(gzip.decompress(raw)).hexdigest()==r['decompressed_sha256']
    figs=[DOC/'assets'/f'{c}_{k}.{e}' for c in ['act','gemm'] for k in ['comparison','zoom','endpoints'] for e in ['png','svg']]
    assert all(p.is_file() for p in figs) and len(figs)==12
    html=(DOC/'report.html').read_text(encoding='utf-8');assert html.count('<figure>')==6 and 'data:image/png;base64,' not in html
    assert 'id="query-data"' not in html
    links=sum(check_links(p) for p in [DOC/'report.html',DOC/'README.md',DOC.parent/'issue-119-pin-xy-candidates.md',REPO/'project/experiments/pin_xy_candidates/README.md'])
    print(f'PASS: {len(rows)} signal rows; A/B/C source/layer/net/direction/geometry, byte grouping, constant/PG preservation; 12 PNG/SVG files; {links} links; {len(manifest["files"])} SHA-bound files.')
    print('Scope: inventory and local geometry evidence only; routing/RC/STA/DRC not validated.')

if __name__=='__main__':main()
