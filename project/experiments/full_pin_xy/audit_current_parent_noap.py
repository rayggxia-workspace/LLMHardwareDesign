"""Read the first actual parent NoAP and its current leaf context; never repair."""
from pathlib import Path
import csv,datetime,json,os,re,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute

DRIVER=Path(__file__).resolve().parent


def run(revision):
    parent=ROOT/'common_integration/actual-access-tips-r01/C'
    pq=json.loads((parent/'execution.json').read_text())
    log=(parent/'lower_route.log').read_text()
    matches=re.findall(r'No access point for (u_[^/\s]+)/([^\s.]+)',log)
    # Match the actual native spelling rather than assume a particular pin.
    if not matches:
        matches=re.findall(r'(u_llaccel_aux)/(bit_\d+)',log)
    assert pq.get('completed_utc') and pq['lower_route_returncode']==1 and 'DRT-0073' in log
    assert matches and len(set(matches))==1
    owner,pin=matches[0];assert owner=='u_llaccel_aux'
    view=ROOT/'llsys_parent_tip_views/r01/llaccel_aux-C'
    vq=json.loads((view/'execution.json').read_text())
    assert vq.get('completed_utc') and vq['source_native_DRC']==0 and vq['all_sources_and_pre_RCX_geometry_unchanged']
    assert pq['views']['llaccel_aux']['source_ODB_SHA']==vq['source_geometry_sha256']
    odb=view/'clean.odb';pins=view/'pins.tsv'
    for p in [odb,pins]:assert sha(p)==vq['files'][p.name]['sha256']
    data=list(csv.DictReader(pins.open(),delimiter='\t'))
    selected=[r for r in data if r['pin']==pin];assert len(selected)==1
    row=selected[0];box=[int(row[k]) for k in ['x0','y0','x1','y1']]
    assert row['layer'] in ['metal5','metal6'] and box[2]-box[0]==box[3]-box[1]==280
    window=[box[0]-12000,box[1]-12000,box[2]+12000,box[3]+12000]
    inputs={str(p):sha(p) for p in [parent/'execution.json',parent/'lower_route.log',view/'execution.json',odb,pins]}
    out=ROOT/'current_parent_noap_context'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'CURRENT_SOURCE_BOUND_NATIVE_NoAP_READ_ONLY_CONTEXT_NOT_REPAIR_OR_AP_PASS',
         'source_SHA':inputs,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
         'scheduler_job':os.environ['SLURM_JOB_ID'],'full_qualification':False,
         'actual_native_error_owner':owner,'actual_native_error_pin':pin,'actual_current_pin':row,
         'source_native_DRC_count':0,'diagnostic_window_DBU':window,
         'all_13507_signal_pin_count':sum(r['use'] not in ['POWER','GROUND'] for r in data),
         'not_checked':['Parent pin access repair','New geometry or route','Full rules or GDS LVS','RC/STA/electrical or complete function']}
    try:
        script=out/'read_actual.tcl'
        script.write_text('set ::env(PINXY_AUDIT_ODB) '+tcl(odb)+'\nset ::env(PINXY_AUDIT_PIN) '+tcl(pin)+'\nset ::env(PINXY_AUDIT_BOX) '+tcl(' '.join(map(str,window)))+'\nset ::env(PINXY_AUDIT_OUT) '+tcl(out/'all_actual_local_metal_PG_OBS.tsv')+'\nsource '+tcl(DRIVER/'audit_parent_region.tcl')+'\nset block [ord::get_db_block]\nset ::env(PINXY_ACCESS_NET_NAMES) '+tcl(pin)+'\nset ::env(PINXY_ACCESS_OUT) '+tcl(out/'actual_error_complete_net.tsv')+'\nsource '+tcl(DRIVER/'export_access.tcl')+'\n')
        common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
        rec['native_read_only_returncode']=execute(common,script,out/'native.log',threads=1)
        if rec['native_read_only_returncode']!=0:raise RuntimeError('Actual read-only native context failed; retain log')
        rows=list(csv.DictReader((out/'all_actual_local_metal_PG_OBS.tsv').open(),delimiter='\t'))
        from collections import Counter
        rec['local_actual_row_count']=len(rows)
        rec['local_actual_roles']=dict(Counter(r['role'] for r in rows))
        rec['local_actual_layers']=dict(Counter(r['layer'] for r in rows))
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==s for p,s in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return 0 if 'actual_failure' not in rec and rec['all_closed_sources_unchanged'] else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
