"""Exact integer M1-M3 OBS union; no pin or other LEF content is changed.

Run in installed KLayout. Geometry equality alone does not prove that every
router treats a different rectangle decomposition identically.
"""
from pathlib import Path
from decimal import Decimal
import datetime,hashlib,json,os,traceback
import pya

out=Path(os.environ['PINXY_OBS_UNION_OUT']);cfg=json.loads((out/'input.json').read_text())
source=Path(cfg['source_LEF']);selected={'metal1','metal2','metal3'}
q={'scope':'ACTUAL_DETAILED_OBS_INTEGER_UNION_ONLY_NOT_DRC_AP_OR_PHYSICAL_QUALIFICATION',
   'klayout_version':pya.__version__,'full_qualification':False,'selected_layers':sorted(selected),
   'source_LEF_SHA256':cfg['source_LEF_SHA256'],'layers':{}}


def coordinate(s):
    n=Decimal(s)*2000
    assert n==n.to_integral_value(),'Source is not exactly representable in original DBU'
    return int(n)


def number(n):return format(Decimal(n)/2000,'f')


try:
    regions={layer:pya.Region() for layer in selected};inside=False;layer=None
    outside=hashlib.sha256();counts={layer:0 for layer in selected}
    with source.open('rb') as f:
        for raw in f:
            t=raw.decode().strip().split()
            if t==['OBS']:inside=True
            elif inside and t and t[0]=='LAYER':
                assert len(t)==3 and t[2]==';';layer=t[1]
            is_selected=inside and layer in selected and t and t[0] in ['RECT','POLYGON']
            if is_selected:
                assert t[0]=='RECT' and len(t)==6 and t[5]==';','Unsupported target OBS syntax is not silently discarded'
                b=list(map(coordinate,t[1:5]));assert b[0]<b[2] and b[1]<b[3]
                regions[layer].insert(pya.Box(*b));counts[layer]+=1
            else:outside.update(raw)
            if inside and t==['END']:inside=False;layer=None
    assert all(counts.values())
    for layer in sorted(selected):
        original=regions.pop(layer);union=original.merged();pieces=union.decompose_trapezoids_to_region()
        rebuilt=pya.Region();n=0
        with (out/(layer+'.rects.lefpart')).open('w') as f,(out/(layer+'.rects.dbu.tsv')).open('w') as tab:
            for poly in pieces.each():
                b=poly.bbox();assert poly.area()==b.area(),'Decomposition contains a non-rectangle; do not replace it by bbox'
                coords=[b.left,b.bottom,b.right,b.top];rebuilt.insert(b);n+=1
                f.write('    RECT '+' '.join(map(number,coords))+' ;\n');tab.write('\t'.join(map(str,coords))+'\n')
        assert (union^rebuilt).is_empty()
        # Independently read decimal output back; catches output/DBU conversion errors.
        written=pya.Region()
        with (out/(layer+'.rects.lefpart')).open() as f:
            for line in f:written.insert(pya.Box(*map(coordinate,line.split()[1:5])))
        assert (union^written).is_empty()
        q['layers'][layer]={'original_RECT_count':counts[layer],'new_RECT_count':n,
                            'original_union_area_DBU2':union.area(),'new_union_area_DBU2':written.area(),
                            'original_vs_decomposed_XOR_empty':True,'original_vs_written_reread_XOR_empty':True}
        print('EXACT_INTEGER_OBS_LAYER',layer,counts[layer],n,flush=True)
        del original,union,pieces,rebuilt,written
    inside=False;layer=None;emitted=set();outside_after=hashlib.sha256()
    with source.open('rb') as f,(out/'compacted_GEOMETRY_ONLY.lef').open('wb') as g:
        for raw in f:
            t=raw.decode().strip().split()
            if t==['OBS']:inside=True
            elif inside and t and t[0]=='LAYER':layer=t[1]
            skip=inside and layer in selected and t and t[0] in ['RECT','POLYGON']
            if skip:
                if layer not in emitted:
                    with (out/(layer+'.rects.lefpart')).open('rb') as compact:
                        for part in compact:g.write(part)
                    emitted.add(layer)
            else:g.write(raw);outside_after.update(raw)
            if inside and t==['END']:inside=False;layer=None
    assert emitted==selected and outside.digest()==outside_after.digest()
    q['all_bytes_outside_selected_OBS_RECT_lines_identical']=True
    q['outside_content_SHA256']=outside.hexdigest()
    q['source_LEF_unchanged']=hashlib.sha256(source.read_bytes()).hexdigest()==cfg['source_LEF_SHA256']
    assert q['source_LEF_unchanged']
except Exception:q['actual_failure']=traceback.format_exc()
q['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
(out/'exact_union.json').write_text(json.dumps(q,indent=2)+'\n')
if q.get('actual_failure'):raise RuntimeError(q['actual_failure'])
