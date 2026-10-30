"""Actual failed-net geometry and old-pin-metal loss, not an implemented repair."""
from pathlib import Path
from collections import Counter
import csv,datetime,gzip,json,os,re,sys,traceback
from run_exports import ROOT,sha
from check_access import check_rows

DRIVER=Path(__file__).resolve().parent


def union_area(boxes):
    xs=sorted({v for b in boxes for v in [b[0],b[2]]});area=0
    for a,z in zip(xs,xs[1:]):
        ys=sorted((b[1],b[3]) for b in boxes if b[0]<z and b[2]>a)
        total=0;lo=hi=None
        for y0,y1 in ys:
            if hi is None:lo,hi=y0,y1
            elif y0>hi:total+=hi-lo;lo,hi=y0,y1
            else:hi=max(hi,y1)
        if hi is not None:total+=hi-lo
        area+=(z-a)*total
    return area


def run(revision):
    before=ROOT/'llsys_parent_access_tip/r01';after=ROOT/'llsys_owned_cap_access/r01'
    bq=json.loads((before/'execution.json').read_text());aq=json.loads((after/'execution.json').read_text())
    assert bq.get('completed_utc') and bq['fresh_DRC_count']==0
    assert aq.get('completed_utc') and aq['fresh_DRC_count']==2 and aq['all_725253_original_WIRE_VIA_rectangle_multisets_identical'] and aq['whole_signal_geometry']['pass']
    drc=after/'independent.drc';assert sha(drc)==aq['files'][drc.name]['sha256']
    names=set(re.findall(r'net:(\S+)',drc.read_text()));assert names=={'bit_433'}
    paths=[before/'execution.json',after/'execution.json',drc,before/'whole_access.tsv.gz',after/'whole_access.tsv.gz']
    for source,q in [(before,bq),(after,aq)]:assert sha(source/'whole_access.tsv.gz')==q['files']['whole_access.tsv.gz']['sha256']
    inputs={str(p):sha(p) for p in paths};out=ROOT/'owned_cap_spacing_diagnosis'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'ACTUAL_NEW_SAME_NET_SPACING_GEOMETRY_DIAGNOSIS_NOT_REPAIR_OR_DRC_PASS','source_SHA':inputs,
         'full_qualification':False,'scheduler_job':os.environ['SLURM_JOB_ID'],'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
         'native_source_DRC_before_after':[0,2],'source_all13507_pins_preserved':True,'actual_failed_nets':sorted(names)}
    try:
        versions=[]
        for label,source in [('before',before),('after',after)]:
            selected=[];seen=set()
            with gzip.open(str(source/'whole_access.tsv.gz'),'rt') as f:
                header=f.readline();fields=header.strip().split('\t')
                with (out/(label+'_failed_nets.tsv')).open('w') as g:
                    g.write(header)
                    for line in f:
                        name=line.split('\t',1)[0]
                        if name in names:g.write(line);selected.append(dict(zip(fields,line.strip().split('\t'))));seen.add(name)
                        elif seen==names:break
            assert seen==names and check_rows(selected,True)['pass'];versions.append(selected)
        key=lambda r:tuple(r[k] for k in ['net','kind','layer','x0','y0','x1','y1','link'])
        physical=lambda rows:Counter(key(r) for r in rows if r['kind'] in ['WIRE','VIA','ITERM'])
        assert physical(versions[0])==physical(versions[1])
        box=lambda r:tuple(int(r[k]) for k in ['x0','y0','x1','y1'])
        old=[r for r in versions[0] if r['kind']=='BTERM'];new=[r for r in versions[1] if r['kind']=='BTERM']
        assert len(old)==len(new)==1 and old[0]['layer']==new[0]['layer']=='metal5'
        p=box(old[0]);n=box(new[0]);assert p!=n and p[2]-p[0]==p[3]-p[1]==280
        covered=[];extensions=[]
        for r in versions[1]:
            if r['layer']!='metal5' or r['kind'] not in ['WIRE','VIA']:continue
            b=box(r);c=(max(b[0],p[0]),max(b[1],p[1]),min(b[2],p[2]),min(b[3],p[3]))
            if c[0]<c[2] and c[1]<c[3]:covered.append(c)
            if r['kind']!='WIRE':continue
            same_y=b[1]==p[1] and b[3]==p[3] and max(b[0],p[0])<=min(b[2],p[2])
            same_x=b[0]==p[0] and b[2]==p[2] and max(b[1],p[1])<=min(b[3],p[3])
            if same_y or same_x:
                merged=(min(b[0],p[0]),min(b[1],p[1]),max(b[2],p[2]),max(b[3],p[3]))
                assert union_area([b,p])==(merged[2]-merged[0])*(merged[3]-merged[1])
                if merged!=b:extensions.append({'actual_old_WIRE_box_DBU':b,'proposed_new_WIRE_box_DBU':merged,'actual_link':r['link'],'layer':'metal5','union_equals_original_wire_plus_old_pin':True})
        rec['actual_target_rows_before_after']=list(map(len,versions))
        rec['all_actual_target_WIRE_VIA_and_internal_endpoints_exact']=True
        rec['old_new_actual_M5_pin_boxes_DBU']=[p,n]
        rec['old_pin_area_DBU2']=280*280;rec['old_pin_covered_by_remaining_WIRE_VIA_DBU2']=union_area(covered)
        rec['actual_old_pin_metal_removed_DBU2']=280*280-union_area(covered)
        rec['proposed_exact_wire_extensions_NOT_IMPLEMENTED']=extensions
        rec['interpretation']='If positive, old BPin metal removal reduced conductor union although every WIRE/VIA was retained. Restoring this metal is a proposed actual wire ECO, not yet DRC-verified.'
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==s for p,s in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return 0 if not rec.get('actual_failure') and rec['all_closed_sources_unchanged'] else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
