"""ACT full-C revision for real adjacent-layer macro pin access.

Manufacturing-grid alignment alone did not give parent access. Snap only the
740 moved C points to actual M5/M6 or M6/M7 track intersections, avoid immutable
PG/OBS, and reserve temporary routing windows on the immediately higher layer.
The windows constrain this NEW leaf route only; original OBS/metal is retained.
"""
from pathlib import Path
import argparse, hashlib, json, shutil
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
import expand_candidates as expand


def prepare(root, out, case='act', candidate_table=None):
    root, out = Path(root), Path(out)
    assert not out.exists(), 'Refuse existing revision'
    expected={'act':860,'gemm':3753,'mxu':2172,'vector':2246,'opentpu_aux':2229,'llaccel_aux':13507}
    assert case in expected
    raw = root/(case+'_pin_coordinates.csv')
    d = pd.read_csv(raw, low_memory=False)
    a = d[d.plan=='A'].set_index('pin')
    c = d[d.plan=='C'].set_index('pin').copy()
    if candidate_table is not None:
        c=pd.read_csv(candidate_table,low_memory=False).set_index('pin').loc[a.index].copy()
    cohort = sorted(c[c.moved].index)
    assert len(a)==len(c)==expected[case] and cohort
    if case=='act' and candidate_table is None:assert len(cohort)==740
    pieces=[]
    for chunk in pd.read_csv(root/'physical'/case/'shapes.tsv.gz',sep='\t',chunksize=250000):
        pieces.append(chunk[chunk.layer.isin(['metal5','metal6','metal7']) & chunk.kind.str.startswith('pg')])
    obs=root/'physical'/case/'obstructions.tsv.gz'
    assert obs.exists(),'Actual macro OBS required, not inferred free space'
    q=pd.read_csv(obs,sep='\t');pieces.append(q[q.layer.isin(['metal5','metal6','metal7'])][['layer','x0','y0','x1','y1','net_id','kind']])
    index=expand.legacy.ShapeIndex(pd.concat(pieces,ignore_index=True))
    meta=json.loads((root/(case+'.meta.json')).read_text());die=np.array(meta['die_dbu'])/2000
    macros=np.array([q['bbox_dbu'] for q in meta['macros']],float).reshape(-1,4)/2000
    windows=[];changes=[]
    c['incremental_revision']='C_'+case+'_access_r03';c['revision_reason']='Original retained C point'
    xy=c[['x_um','y_um']].to_numpy(float).copy();neighbors=cKDTree(xy);row_index={p:i for i,p in enumerate(c.index)}
    for key in ['toM6_existing_shape_risk','toM8_existing_shape_risk','toM10_existing_shape_risk']:
        c[key]=c[key].astype(object)
    for pin in cohort:
        r=c.loc[pin];old=np.array([r.x_um,r.y_um]);hx=(r.x1_um-r.x0_um)/2;hy=(r.y1_um-r.y0_um)/2
        assert r.layer in ['metal5','metal6']
        adjacent='metal6' if r.layer=='metal5' else 'metal7'
        yp=.28 if r.layer=='metal5' else .8
        # These are the actual platform make_tracks.tcl rules, not inferred
        # from grey layout backgrounds or a single highest-layer via pitch.
        sx=.095+round((old[0]-.095)/.28)*.28;sy=.07+round((old[1]-.07)/yp)*yp
        half=.21 if adjacent=='metal6' else .6
        current_index=row_index[pin]
        options=sorted((abs(i*.28)+abs(j*yp),i,j) for i in range(-12,13) for j in range(-6,7))
        chosen=None
        for _,i,j in options:
            x,y=round(sx+i*.28,6),round(sy+j*yp,6)
            b=np.array([x-hx,y-hy,x+hx,y+hy])
            if min(b[:2])<5 or b[2]>die[2]-5 or b[3]>die[3]-5:continue
            if len(macros) and np.any((b[0]-.56<macros[:,2])&(b[2]+.56>macros[:,0])&(b[1]-.56<macros[:,3])&(b[3]+.56>macros[:,1])):continue
            nearby=[i for i in neighbors.query_ball_point([x,y],10.) if i!=current_index]
            others=xy[nearby]
            separation=.56 if adjacent=='metal6' or case=='act' else .84
            if np.any((abs(others[:,0]-x)<separation-1e-8)&(abs(others[:,1]-y)<separation-1e-8)):continue
            if index.hits(r.layer,x,y,hx,hy,.14,int(r.net_id)):continue
            if index.hits(adjacent,x,y,half,half,0,int(r.net_id)):continue
            chosen=(x,y);break
        if chosen is None:
            failure=out.with_suffix('.failure.json')
            if not failure.exists():
                failure.write_text(json.dumps({'status':'LOCAL_CANDIDATE_SEARCH_FAILED_NOT_A_PHYSICAL_RESULT','case':case,'pin':pin,
                    'old_C_xy_um':old.tolist(),'original_pin_layer':r.layer,'adjacent_layer':adjacent,
                    'all_signal_pins':expected[case],'selected_cohort':len(cohort),'completed_candidates_before_failure':len(windows),
                    'generator_file_SHA':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2)+'\n')
            raise AssertionError((pin,'No fixed-PG/OBS-clear adjacent-layer access site'))
        x,y=chosen
        xy[current_index]=[x,y]
        c.loc[pin,['x_um','y_um','x0_um','y0_um','x1_um','y1_um']]=[x,y,x-hx,y-hy,x+hx,y+hy]
        c.loc[pin,'revision_reason']='Actual neighboring-layer track intersection and fixed-PG/OBS clearance; original pin layer/size retained; temporary upper access window requires real reroute'
        for key in ['toM6_existing_shape_risk','toM8_existing_shape_risk','toM10_existing_shape_risk']:
            c.loc[pin,key]='UNKNOWN_NEW_ROUTE_AND_PARENT_ACCESS'
        windows.append({'pin':pin,'original_pin_layer':r.layer,'reservation_layer':adjacent,'bbox_um':[x-half,y-half,x+half,y+half],
                        'purpose':'Temporary leaf-routing keepout for future parent AP; not a physical conductor or an original OBS',
                        'actual_adjacent_via':'via5_0' if adjacent=='metal6' else 'via6_0',
                        'window_width_um':2*half,'rules':'M6: 0.14um landing + 2x0.14um guard; M7: 0.4um wire envelope + 2x0.4um guard; full native rules remain mandatory'})
        changes.append({'pin':pin,'layer':r.layer,'old_C_xy_um':old.tolist(),'proposed_xy_um':[x,y]})
    c['moved']=(abs(c.x_um-a.x_um)>1e-6)|(abs(c.y_um-a.y_um)>1e-6)
    original_shapes=pd.read_csv(root/'physical'/case/'shapes.tsv.gz',sep='\t')
    original_shapes=original_shapes[original_shapes.layer.isin(['metal5','metal6','metal7'])]
    full_index=expand.legacy.ShapeIndex(original_shapes)
    for pin in cohort:
        r=c.loc[pin];hx=(r.x1_um-r.x0_um)/2;hy=(r.y1_um-r.y0_um)/2
        c.loc[pin,'pin_layer_overlap']=bool(full_index.hits(r.layer,r.x_um,r.y_um,hx,hy,0,int(r.net_id)))
        c.loc[pin,'pin_layer_basic_spacing_risk']=bool(full_index.hits(r.layer,r.x_um,r.y_um,hx,hy,.14,int(r.net_id)))
        c.loc[pin,'macro_bbox_overlap']=False
        c.loc[pin,'retention_or_movement_reason']=c.loc[pin,'revision_reason']
    for name,column in [('anchors','nearest_traced_endpoint_L1_um'),('endpoints','nearest_direct_endpoint_L1_um')]:
        points=pd.read_csv(root/'physical'/case/(name+'.tsv.gz'),sep='\t');points.pin=points.pin.map(expand.legacy.norm)
        lookup={p:g[['x','y']].to_numpy(float)/2000 for p,g in points.groupby('pin')}
        for pin in cohort:
            pp=lookup.get(pin,np.empty((0,2)))
            c.loc[pin,column]=float(abs(pp-c.loc[pin,['x_um','y_um']].to_numpy(float)).sum(axis=1).min()) if len(pp) else np.nan
    assert int(c.moved.sum())==len(cohort) and len(set(map(tuple,c[['x_um','y_um']].to_numpy())))==expected[case]
    assert all(c[k].equals(a[k]) for k in ['layer','direction','use','net','net_id'])
    assert np.allclose(c.x1_um-c.x0_um,a.x1_um-a.x0_um) and np.allclose(c.y1_um-c.y0_um,a.y1_um-a.y0_um)
    out.mkdir(parents=True)
    c.reset_index().to_csv(out/(case+'_C_access_r03_all_pins.csv'),index=False,float_format='%.6f')
    c.loc[cohort].reset_index().to_csv(out/(case+'-C.csv'),index=False,float_format='%.6f')
    with (out/(case+'-C.tcl')).open('w',encoding='utf-8',newline='\n') as f:
        for pin,r in c.loc[cohort].iterrows():f.write('lappend relocations {'+f'{{{pin}}} {r.layer} {r.x_um:.6f} {r.y_um:.6f} {r.x1_um-r.x0_um:.6f} {r.y1_um-r.y0_um:.6f}'+'}\n')
    with (out/'access_reservations.tcl').open('w',encoding='utf-8',newline='\n') as f:
        for q in windows:f.write('lappend access_reservations {'+q['reservation_layer']+' '+' '.join(format(v,'.6f') for v in q['bbox_um'])+'}\n')
    receipt={'scope':'PROPOSED_ADJACENT_LAYER_ACCESS_REVISION_NOT_PHYSICALLY_QUALIFIED','case':case,'signal_pins':expected[case],'moved_pin_count':len(cohort),
             'method_evidence':'ACT actual escape fixture r02 C: DRT-0073 No access point u_macro/r_data[342]. Other blocks require their own actual access tests; no unobserved failure is asserted.',
             'source_C_SHA':hashlib.sha256(Path(candidate_table if candidate_table else raw).read_bytes()).hexdigest(),'changes':changes,'windows':windows,
             'generator_file_SHA':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'candidate_spacing_note':'M7 candidate centers use0.84um heuristic (0.4um via7 cut+0.44um cut spacing), not the old arbitrary1.12um screen. Actual routing/DRC is unchanged and remains mandatory. ACT retains its already-executed recipe.',
             'routing_method':'Reroute all signal/clock nets around newly created temporary windows; original cells/PG/OBS/layers/rectangles untouched. Remove only these new constraints after routing, verify original block-OBS list unchanged.',
             'track_phase_requirement':'Parent R0 translation must preserve 0.28/0.8/1.6um upper-track phases, e.g. multiples of11.2um; .005um manufacturing grid alone is insufficient',
             'not_checked':['Actual new route','Native DRC','Via/parent pin access','PG/whole connectivity','RC/STA','GDS/full rules']}
    (out/'revision.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (out/'selection.json').write_text(json.dumps({case:{'pins':cohort,**receipt}},indent=2)+'\n')
    shutil.copy2(root/'coverage_gate.json',out/'coverage_gate.json')
    (out/'input_hashes.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()},indent=2)+'\n')
    print('ACCESS_REVISION_PROPOSED',case,len(c),'pins;',len(windows),'temporary adjacent-layer windows; NOT physical pass')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',required=True);p.add_argument('--case',default='act');p.add_argument('--candidate-table');a=p.parse_args();prepare(a.root,a.out,a.case,a.candidate_table)
