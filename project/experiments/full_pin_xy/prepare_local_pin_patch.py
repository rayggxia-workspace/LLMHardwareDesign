"""Incremental repair of three pins implicated by four actual LL native markers.

Reuse the already-computed adjacent-track positions only for those three read
data pins. Keep the other13,504 PG-revision points and the full interface.
This is a new proposal; existing routes/native rules must still be checked.
"""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
import pandas as pd


def prepare(root,out):
    root,out=Path(root),Path(out);assert not out.exists()
    base=root/'trial-inputs-llsys-pg-r03/llaccel_aux_C_pg_r03_all_pins.csv'
    window=root/'trial-inputs-llaccel_aux-access-r04/llaccel_aux_C_access_r03_all_pins.csv'
    a=pd.read_csv(base,low_memory=False).set_index('pin');b=pd.read_csv(window,low_memory=False).set_index('pin')
    names=['bit_1382013','bit_6907','bit_1389626'];c=a.copy();coords=['x_um','y_um','x0_um','y0_um','x1_um','y1_um']
    assert len(a)==len(b)==13507 and set(a.index)==set(b.index)
    mapping=json.loads((root/'inventory/pin_logical_mapping.json').read_text())['llaccel_aux']
    changes=[]
    for pin in names:
        assert mapping[pin]['semantic_bus'] in ['gemm_w_rdata','bank_rdata','vec_rd0_rdata']
        c.loc[pin,coords]=b.loc[pin,coords]
        changes.append({'pin':pin,'semantic_mapping':mapping[pin],'old_xy_um':a.loc[pin,['x_um','y_um']].tolist(),
                        'proposed_xy_um':c.loc[pin,['x_um','y_um']].tolist(),'layer':c.loc[pin,'layer']})
    for key in ['layer','direction','net','use']:assert a[key].equals(c[key])
    assert np.allclose(a.x1_um-a.x0_um,c.x1_um-c.x0_um) and np.allclose(a.y1_um-a.y0_um,c.y1_um-c.y0_um)
    assert len(set(zip(c.x_um,c.y_um,c.layer)))==13507 and int(c.moved.sum())==13184
    out.mkdir(parents=True)
    c.reset_index().to_csv(out/'llaccel_aux_C_local_patch_r01_all_pins.csv',index=False,float_format='%.6f')
    lines=[]
    for pin in names:
        r=c.loc[pin];lines.append('lappend relocations {{'+pin+'} '+r.layer+' '+format(r.x_um,'.6f')+' '+format(r.y_um,'.6f')+' .140000 .140000}')
    (out/'llaccel_aux-C.tcl').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    (out/'revision.json').write_text(json.dumps({'scope':'PROPOSED_3_PIN_LOCAL_REPAIR_OF_ACTUAL_4_NATIVE_MARKERS_NOT_PHYSICAL_PASS',
        'case':'llaccel_aux','source_full_C':'llsys-pg-r03','full_signal_pins':13507,'original_boundary_moved_pins':13184,
        'changed_from_previous_full_C':3,'actual_failed_native_markers':4,'changes':changes,
        'original_layers_shapes_functions_directions_and_logical_peers_preserved':True,
        'group_note':'Three real read-data interfaces; no strobe on these bits. Local displacement retains original bus association, not invented lanes.',
        'source_input_SHA':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [base,window]},
        'not_claimed':['native DRC pass','routed access','STA/electrical pass','full manufacturing rules']},indent=2)+'\n',encoding='utf-8')
    print('LOCAL_PATCH_PROPOSED',len(c),'pins; 13184 internal moves retained; exactly3 new points')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',required=True);a=p.parse_args();prepare(a.root,a.out)
