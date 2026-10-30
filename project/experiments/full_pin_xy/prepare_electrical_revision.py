"""Incremental GEMM C revision after actual full-C max-capacitance failures.

Keep PR120 A/B/C files untouched. Restore whole verified write-byte groups for
the two failing strobe drivers. Retain identical 3039-pin reroute cohort and all
3753 signal pins; actual changed XY becomes 3021. No buffering or master edits.
"""
from pathlib import Path
import argparse,hashlib,json,shutil
import pandas as pd

def prepare(root,out):
    root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    matches=sorted((root/'trial_receipts').glob('*/trials/full-other-r01/gemm-C'));assert matches,'Original full-C failure receipts required'
    prior=matches[-1]
    checks=(prior/'timing.checks.txt').read_text();assert 'max capacitance' in checks
    failures=[s for s in checks.splitlines() if '(VIOLATED)' in s];assert len(failures)==2
    access=json.loads((prior/'access.json').read_text());assert access['pass']
    affected={};pins=[]
    for line in failures:
        driver=line.split()[0];hits=[]
        for net,record in access['nets'].items():
            terms=[t for g in record['terminal_groups'] for t in g]
            if 'I:'+driver in terms:hits.append((net,[t[2:] for t in terms if t.startswith('B:')]))
        assert len(hits)==1 and len(hits[0][1])==1
        pin=hits[0][1][0];assert pin.startswith('gemm_wr_wstrb[')
        pins.append(pin);affected[pin]={'actual_driver':driver,'actual_net':hits[0][0],'reported_max_capacitance_line':line}
    assert set(pins)=={'gemm_wr_wstrb[29]','gemm_wr_wstrb[30]'}
    table=pd.read_csv(root/'gemm_pin_coordinates.csv',low_memory=False)
    a=table[table.plan=='A'].set_index('pin');c=table[table.plan=='C'].set_index('pin').copy()
    groups=pd.read_csv(root/'gemm_groups.csv');groups=groups[groups.plan=='C']
    restore=set()
    for pin in pins:
        group=groups[groups.pin==pin].group.iloc[0];members=set(groups[groups.group==group].pin)
        byte=int(pin.split('[')[1].rstrip(']'))
        assert members=={pin}|{'gemm_wr_wdata['+str(i)+']' for i in range(byte*8,(byte+1)*8)},'Do not invent byte/strobe semantics'
        restore|=members;affected[pin]['verified_original_group']=group;affected[pin]['restored_whole_byte_pins']=sorted(members)
    assert len(restore)==18
    cohort=sorted(c[c.moved].index);assert len(cohort)==3039 and restore<=set(cohort)
    c['previous_PR120_C_x_um']=c.x_um;c['previous_PR120_C_y_um']=c.y_um
    for pin in restore:
        # Reuse the actual A geometry metrics at the restored A coordinate,
        # rather than leaving C distances/risks attached to the new position.
        for k in a.columns:c.loc[pin,k]=a.loc[pin,k]
        c.loc[pin,'plan']='C';c.loc[pin,'moved']=False
    c['incremental_revision']='C_electrical_r03';c['revision_reason']='Unchanged PR120 C coordinates'
    c.loc[sorted(restore),'revision_reason']='Restore complete real write byte29/30 to original boundary after actual max-capacitance failure; no drive/buffer/cell changes'
    assert len(c)==3753 and int(c.moved.sum())==3021
    assert len(set(map(tuple,c[['x_um','y_um']].to_numpy())))==3753
    c.reset_index().to_csv(out/'gemm_C_electrical_r03_all_pins.csv',index=False,float_format='%.6f')
    selected=c.loc[cohort]
    selected.reset_index().to_csv(out/'gemm-C.csv',index=False,float_format='%.6f')
    with (out/'gemm-C.tcl').open('w',encoding='utf-8',newline='\n') as f:
        for pin,r in selected.iterrows():
            f.write('lappend relocations {'+f'{{{pin}}} {r.layer} {r.x_um:.6f} {r.y_um:.6f} {r.x1_um-r.x0_um:.6f} {r.y1_um-r.y0_um:.6f}'+'}\n')
    shutil.copy2(root/'coverage_gate.json',out/'coverage_gate.json')
    receipt={'scope':'Incremental physical C revision, not replacement of published PR120 A/B/C','selected_matched_cohort':3039,'actual_proposed_moved_count':3021,
      'all_signal_pin_count':3753,'restored_to_original_boundary':sorted(restore),'actual_failure_evidence':affected,
      'source_coordinate_sha256':hashlib.sha256((root/'gemm_pin_coordinates.csv').read_bytes()).hexdigest(),
      'source_trial_receipt_sha256':hashlib.sha256((prior/'execution.json').read_bytes()).hexdigest(),
      'unchanged':'Function/net/direction/layer/size/constants and original cell master/placement/CTS/PDN; only 18 XY restored; all other original C XY unchanged',
      'physical_qualification':'NOT_YET_VERIFIED; new real reroute/RC/STA/native DRC/connectivity still required'}
    (out/'selection.json').write_text(json.dumps({'gemm':{'pins':cohort,**receipt}},indent=2)+'\n')
    (out/'revision.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (out/'input_hashes.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()},indent=2)+'\n')
    print('GEMM_INCREMENTAL_C3',len(c),'pins',len(cohort),'matched cohort',int(c.moved.sum()),'proposed moves')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',required=True);a=p.parse_args();prepare(a.root,a.out)
