"""Verify actual moved pin rectangles contact immutable original PG conductors.

This is a direct same-layer metal intersection proof, not a complete DRC run.
It can reject a known-invalid pure-XY trial before spending further DRT time.
Actual moved fingerprints, original export SHA and unchanged PG are required.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,tkinter
import pandas as pd
import expand_candidates as expand

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(root,case,actual,out):
    root=Path(root);actual=Path(actual);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    receipt=json.loads((root/'physical'/case/'receipt.json').read_text(encoding='utf-8'))
    execution=json.loads((actual/'execution.json').read_text(encoding='utf-8'))
    assert receipt['source_sha256']==execution['source_sha256']
    assert (actual/'before.pdn.tsv').read_bytes()==(actual/'moved.pdn.tsv').read_bytes(),'PG changed before routing'
    tcl=tkinter.Tcl();records=[tcl.splitlist(s) for s in (actual/'moved.pins.tsv').read_text().splitlines()]
    records=[r for r in records if r[2] not in ['POWER','GROUND']]
    got={r[0].replace('\\',''):r for r in records};assert len(got)==len(records)
    raw=pd.read_csv(root/(case+'_pin_coordinates.csv'),low_memory=False);c=raw[raw.plan=='C'].set_index('pin')
    assert set(got)==set(c.index)
    for pin,r in c.iterrows():
        q=got[pin];assert (q[1],q[2],q[3].replace('\\',''),q[4])==(r.direction,r['use'],r.net,r.layer)
        assert all(abs(int(q[i+5])/2000-r[k+'_um'])<1e-6 for i,k in enumerate(['x0','y0','x1','y1']))
    pg=[]
    for chunk in pd.read_csv(root/'physical'/case/'shapes.tsv.gz',sep='\t',chunksize=250000):
        pg.append(chunk[chunk.layer.isin(['metal5','metal6']) & chunk.kind.str.startswith('pg')])
    pg=pd.concat(pg,ignore_index=True);index=expand.legacy.ShapeIndex(pg)
    b=pd.read_csv(root/'physical'/case/'bterms.tsv.gz',sep='\t')
    net_names=dict(zip(b.net_id,b.net));contacts=[]
    for pin,q in got.items():
        box=[int(v)/2000 for v in q[5:9]]
        for idx,kind in index.query(q[4],box):
            rect,nets,kinds,bins=index.layers[q[4]];j=int(nets[idx]);name=net_names.get(j,'UNKNOWN_PG_NET_ID_'+str(j))
            assert name in ['VDD','VSS'],('PG ownership not established',j,name)
            contacts.append({'pin':pin,'signal_net':q[3],'layer':q[4],'actual_pin_box_um':box,'fixed_PG_net':name,'PG_shape_box_um':rect[idx].tolist(),'PG_shape_kind':kind})
    report={'scope':'ACTUAL_MOVED_PINS_DIRECT_FIXED_PG_METAL_CONTACT; not a complete DRC run','case':case,'scheduler_job':execution['scheduler_job'],
       'original_odb_sha256':receipt['source_sha256'],'original_geometry_export_receipt_sha256':sha(root/'physical'/case/'receipt.json'),
       'all_actual_moved_pins_match_complete_original_C':True,'signal_pins_checked':len(got),'actual_PG_before_and_after_move_byte_identical':True,
       'before_PG_sha256':sha(actual/'before.pdn.tsv'),'moved_PG_sha256':sha(actual/'moved.pdn.tsv'),'moved_pins_sha256':sha(actual/'moved.pins.tsv'),
       'direct_contact_pin_count':len({r['pin'] for r in contacts}),'direct_contact_rectangle_pairs':len(contacts),'contacts':contacts,
       'conclusion':'KNOWN_INVALID_WITH_FIXED_PG: signal and power metal overlap on the same layer; DRT cannot repair an immovable pin/PG rectangle overlap' if contacts else 'NO_DIRECT_CONTACT_FOUND; full DRC and via/spacing checks still required'}
    (out/'proof.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    pd.DataFrame(contacts).to_csv(out/'direct_contacts.csv',index=False)
    print('ACTUAL_FIXED_PG_CONTACTS',case,report['signal_pins_checked'],report['direct_contact_pin_count'],report['direct_contact_rectangle_pairs'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--case',required=True);p.add_argument('--actual',required=True);p.add_argument('--out',required=True);a=p.parse_args();run(a.root,a.case,a.actual,a.out)
