"""Choose one actual-geometry-screened parent landing on the source side of PG.

ACT original M6 leaf pin stays fixed. Only the NEW parent M10 intermediate
landing moves. Full native spacing/via/route validation remains mandatory.
"""
from pathlib import Path
import argparse,csv,gzip,hashlib,json


def prepare(source,out):
    source,out=Path(source),Path(out);assert not out.exists()
    def rows(name):return list(csv.DictReader(gzip.open(source/name,'rt'),delimiter='\t'))
    wires=rows('whole_access.tsv.gz');net='r_data[195]'
    original=next(q for q in wires if q['net']==net and q['kind']=='BTERM')
    terminal=next(q for q in wires if q['net']==net and q['kind']=='ITERM')
    assert original['layer']=='metal10' and terminal['layer']=='metal6'
    endpoint=[(int(terminal[k+'0'])+int(terminal[k+'1']))/4000 for k in ['x','y']]
    obstacles=[]
    for q in wires:
        if q['net']!=net and q['layer']=='metal10':obstacles.append([int(q[k])/2000 for k in ['x0','y0','x1','y1']])
    for q in rows('parent_M10_PG.tsv.gz'):obstacles.append([int(q[k])/2000 for k in ['x0','y0','x1','y1']])
    for q in rows('u_macro-pg-access-obstructions.tsv.gz'):
        if q['layer']=='metal10':obstacles.append([int(q[k])/2000 for k in ['xmin_dbu','ymin_dbu','xmax_dbu','ymax_dbu']])
    candidates=[]
    for i in range(-15,16):
        for j in range(-15,16):
            x=.095+(round((endpoint[0]-.095)/3.2)+i)*3.2;y=.07+(round((endpoint[1]-.07)/3.2)+j)*3.2
            # Source is right of the proven parent VDD stripe ending147.77um.
            if x-.4<147.77+1.5:continue
            b=[x-.4,y-.4,x+.4,y+.4]
            if not any(b[0]-1.5<q[2] and b[2]+1.5>q[0] and b[1]-1.5<q[3] and b[3]+1.5>q[1] for q in obstacles):
                candidates.append((abs(x-endpoint[0])+abs(y-endpoint[1]),x,y))
    assert candidates,'No static-geometry-screened same-side landing; do not invent a free region'
    _,x,y=min(candidates);out.mkdir(parents=True)
    rec={'scope':'NEW_PARENT_LANDING_XY_ONLY_NOT_LEAF_PIN_LAYER_CHANGE','net':net,'original_leaf_layer':'metal6','leaf_parent_xy_um':endpoint,
         'old_parent_xy_um':[(int(original[k+'0'])+int(original[k+'1']))/4000 for k in ['x','y']],
         'new_parent_xy_um':[round(x,6),round(y,6)],'parent_layer':'metal10','parent_size_um':[.8,.8],
         'static_M10_guard_um':1.5,'guard_basis':'Actual M10 maximum PRL spacing1.5um, only applied to this M10 parent landing; not all leaf pins',
         'screened_geometry':'Actual other-net M10 wire/via/BTerm/ITerm, actual parent M10 PG, actual macro M10 OBS. New routes/vias remain unverified.',
         'source_files_SHA':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.iterdir() if p.name in ['whole_access.tsv.gz','parent_M10_PG.tsv.gz','u_macro-pg-access-obstructions.tsv.gz']},
         'source_files_uncompressed_SHA':{p.name:hashlib.sha256(gzip.decompress(p.read_bytes())).hexdigest() for p in source.iterdir() if p.name in ['whole_access.tsv.gz','parent_M10_PG.tsv.gz','u_macro-pg-access-obstructions.tsv.gz']},
         'full_qualification':False}
    (out/'landing_delta.json').write_text(json.dumps(rec,indent=2)+'\n')
    print('NEW_PARENT_LANDING_PROPOSED',rec['old_parent_xy_um'],'->',rec['new_parent_xy_um'],'native validation pending')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',required=True);a=p.parse_args();prepare(a.source,a.out)
