"""Evidence-driven MXU revision, preserving the entire 1964-pin reroute cohort.

Keep the verified 32-bit TMEM lane0 and its enable on the original boundary
after five real driver max-capacitance failures. Move two PG-colliding points
locally inside the same block, screened against actual original M5 geometry.
Original A/B/C publications remain untouched. This proposal still needs routing.
"""
from pathlib import Path
import argparse,gzip,hashlib,json,shutil
import numpy as np
import pandas as pd
import expand_candidates as expand

def prepare(root,out):
    root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    prior=root/'trial_receipts/milestone-r07/trials/full-other-r01/mxu-C'
    text=(prior/'timing.checks.txt').read_text();assert 'max capacitance' in text
    violations=[s for s in text.splitlines() if '(VIOLATED)' in s];assert len(violations)==5
    access=json.loads((prior/'access.json').read_text());assert access['pass']
    cap_pins={}
    for line in violations:
        driver=line.split()[0];found=[]
        for net,r in access['nets'].items():
            terms=[t for g in r['terminal_groups'] for t in g]
            if 'I:'+driver in terms:found += [t[2:] for t in terms if t.startswith('B:')]
        assert len(found)==1;cap_pins[found[0]]={'actual_driver':driver,'native_max_capacitance_report':line}
    assert set(cap_pins)=={'t_wdata['+str(i)+']' for i in [5,6,7,8,13]}
    table=pd.read_csv(root/'mxu_pin_coordinates.csv',low_memory=False)
    a=table[table.plan=='A'].set_index('pin');c=table[table.plan=='C'].set_index('pin').copy()
    cohort=sorted(c[c.moved].index);assert len(cohort)==1964
    groups=pd.read_csv(root/'mxu_groups.csv');groups=groups[groups.plan=='C']
    lane=groups[groups.pin=='t_wdata[5]'].group.iloc[0]
    restore=set(groups[groups.group==lane].pin)
    assert restore=={'t_wdata['+str(i)+']' for i in range(32)}|{'t_wen[0]'},'Must retain the real 32-bit data/enable association'
    c['previous_C_x_um']=c.x_um;c['previous_C_y_um']=c.y_um
    c['incremental_revision']='C_mxu_repair_r03';c['revision_reason']='Unchanged original C XY'
    for pin in restore:
        for k in ['x_um','y_um','x0_um','y0_um','x1_um','y1_um']:c.loc[pin,k]=a.loc[pin,k]
        c.loc[pin,'revision_reason']='Restore entire verified TMEM write lane0+enable after actual five max-capacitance failures'
    # Only load the actual layer used by the two reported PG collisions.
    pieces=[]
    for chunk in pd.read_csv(root/'physical/mxu/shapes.tsv.gz',sep='\t',chunksize=250000):pieces.append(chunk[chunk.layer.isin(['metal5','metal6'])])
    obs=root/'physical/mxu/obstructions.tsv.gz'
    if obs.exists():
        frame=pd.read_csv(obs,sep='\t');pieces.append(frame[frame.layer.isin(['metal5','metal6'])][['layer','x0','y0','x1','y1','net_id','kind']])
    index=expand.legacy.ShapeIndex(pd.concat(pieces,ignore_index=True));del pieces
    meta=json.loads((root/'mxu.meta.json').read_text());dims=np.array(meta['die_dbu'])/2000
    macros=np.array([r['bbox_dbu'] for r in meta['macros']],float).reshape(-1,4)/2000
    for key in ['toM6_existing_shape_risk','toM8_existing_shape_risk','toM10_existing_shape_risk']:c[key]=c[key].astype(object)
    screen={};pg_pins=['pf_uv[109]','b_rdata[174]']
    for pin in pg_pins:
        row=c.loc[pin];assert row.layer=='metal5' and row.net==pin
        original=np.array([row.x_um,row.y_um]);others=c.drop(index=pin)[['x_um','y_um']].to_numpy()
        options=sorted([(abs(dx)+abs(dy),dx,dy) for dx in [-2.24,-1.12,0,1.12,2.24] for dy in [-2.24,-1.12,0,1.12,2.24] if dx or dy])
        chosen=None
        for _,dx,dy in options:
            x,y=np.round((original+[dx,dy])/.005)*.005
            box=np.array([x-.07,y-.07,x+.07,y+.07])
            if box[0]<22 or box[1]<22 or box[2]>dims[2]-22 or box[3]>dims[3]-22:continue
            if len(macros) and np.any((box[0]-.56<macros[:,2])&(box[2]+.56>macros[:,0])&(box[1]-.56<macros[:,3])&(box[3]+.56>macros[:,1])):continue
            if np.any((abs(others[:,0]-x)<.56)&(abs(others[:,1]-y)<.56)):continue
            if index.hits('metal5',x,y,.07,.07,.14,int(row.net_id)):continue
            chosen=(x,y);break
        assert chosen,(pin,'No actual-original-M5 screened local repair; do not pretend free space')
        x,y=chosen;c.loc[pin,['x_um','y_um','x0_um','y0_um','x1_um','y1_um']]=[x,y,x-.07,y-.07,x+.07,y+.07]
        c.loc[pin,'revision_reason']='Local internal M5 point repair after independent native DRC signal-to-VDD short; actual original M5 geometry/basic-spacing screened, new routing unverified'
        c.loc[pin,['pin_layer_overlap','pin_layer_basic_spacing_risk','macro_bbox_overlap']]=False
        for k in ['toM6_existing_shape_risk','toM8_existing_shape_risk','toM10_existing_shape_risk']:c.loc[pin,k]='UNKNOWN_FOR_INCREMENTAL_XY'
        screen[pin]={'old_C_xy_um':original.tolist(),'new_proposed_xy_um':[float(x),float(y)],'layer':'metal5','screened_half_pin_size_um':[.07,.07],
          'basic_spacing_um':.14,'scope':'All actual-original M5 shapes including PG and available OBS; not post-repair route, via, full DRC or parent accessibility.'}
    c['moved']=(abs(c.x_um-a.x_um)>1e-6)|(abs(c.y_um-a.y_um)>1e-6)
    for pin in restore|set(pg_pins):
        r=c.loc[pin];hx=(r.x1_um-r.x0_um)/2;hy=(r.y1_um-r.y0_um)/2
        c.loc[pin,'pin_layer_overlap']=bool(index.hits(r.layer,r.x_um,r.y_um,hx,hy,0,int(r.net_id)))
        c.loc[pin,'pin_layer_basic_spacing_risk']=bool(index.hits(r.layer,r.x_um,r.y_um,hx,hy,.14,int(r.net_id)))
        if pin in restore:
            for key in ['toM6_existing_shape_risk','toM8_existing_shape_risk','toM10_existing_shape_risk']:c.loc[pin,key]=a.loc[pin,key]
    for filename,column in [('anchors','nearest_traced_endpoint_L1_um'),('endpoints','nearest_direct_endpoint_L1_um')]:
        points=pd.read_csv(root/'physical/mxu'/(filename+'.tsv.gz'),sep='\t');points.pin=points.pin.map(expand.legacy.norm)
        for pin in restore|set(pg_pins):
            p=points[points.pin==pin][['x','y']].to_numpy(float)/2000
            c.loc[pin,column]=float(abs(p-c.loc[pin,['x_um','y_um']].to_numpy(float)).sum(axis=1).min()) if len(p) else np.nan
    assert len(c)==2172 and int(c.moved.sum())==1931 and len(set(map(tuple,c[['x_um','y_um']].to_numpy())))==2172
    c.reset_index().to_csv(out/'mxu_C_repair_r03_all_pins.csv',index=False,float_format='%.6f')
    selected=c.loc[cohort];selected.reset_index().to_csv(out/'mxu-C.csv',index=False,float_format='%.6f')
    with (out/'mxu-C.tcl').open('w',encoding='utf-8',newline='\n') as f:
        for pin,r in selected.iterrows():f.write('lappend relocations {'+f'{{{pin}}} {r.layer} {r.x_um:.6f} {r.y_um:.6f} {r.x1_um-r.x0_um:.6f} {r.y1_um-r.y0_um:.6f}'+'}\n')
    shutil.copy2(root/'coverage_gate.json',out/'coverage_gate.json')
    receipt={'scope':'Incremental MXU repair; original A/B/C intact. No cell, driver, storage, clock, PDN or layer changes. Still unverified physically.',
      'all_signal_pins':2172,'selected_original_C_cohort':1964,'actual_proposed_moved_count':1931,'restored_real_lane0_pins':sorted(restore),
      'actual_capacitance_failures':cap_pins,'actual_independent_DRC_evidence':'Three metal5 signal-to-VDD Shorts, pf_uv[109] and b_rdata[174], retained under full-other-r01.',
      'local_geometric_repair_screen':screen,'source_C_coordinate_sha256':hashlib.sha256((root/'mxu_pin_coordinates.csv').read_bytes()).hexdigest(),
      'actual_failure_receipt_sha256':hashlib.sha256((prior/'execution.json').read_bytes()).hexdigest()}
    (out/'revision.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (out/'selection.json').write_text(json.dumps({'mxu':{'pins':cohort,**receipt}},indent=2)+'\n')
    (out/'input_hashes.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()},indent=2)+'\n')
    print('MXU_INCREMENTAL_REPAIR',len(c),'signals',len(cohort),'matched cohort',int(c.moved.sum()),'proposed moves',screen)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',required=True);a=p.parse_args();prepare(a.root,a.out)
