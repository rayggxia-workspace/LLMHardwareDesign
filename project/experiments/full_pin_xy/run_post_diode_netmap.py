"""Correlate remaining real-deck findings with the exact matching routed source.

Read-only repair diagnosis. Existing diode membership is not an LVS proof.
Never apply an old GDS polygon to a newer, differently routed database.
"""
from pathlib import Path
import datetime,json,os,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,sha

DRIVER=Path(__file__).resolve().parent


def run(revision,source_kind):
    assert source_kind in ['diode','cap']
    stream=ROOT/'antenna_diode_stream'/('r01' if source_kind=='diode' else 'cap-r01')/'gemm-C'
    physical=ROOT/('antenna_diode_eco' if source_kind=='diode' else 'diode_cap_eco')/'r01/gemm-C'
    out=ROOT/'post_diode_netmap'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'MATCHED_POST_DIODE_REAL_GDS_POLYGON_DIAGNOSIS_NOT_REPAIR_OR_LVS',
      'source_kind':source_kind,'full_qualification':False,'scheduler_job':os.environ['SLURM_JOB_ID'],
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
      'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        sp=stream/'execution.json';pp=physical/'execution.json'
        s=json.loads(sp.read_text());p=json.loads(pp.read_text())
        assert s.get('completed_utc') and p.get('completed_utc')
        assert s['merge_returncode']==s['DRC_returncode']==0
        assert s['source_receipt_SHA']==sha(pp) and s['source_receipt_and_DEF_unchanged']
        assert s['source_DEF_SHA']==sha(physical/'routed.def')==p['files']['routed.def']['sha256']
        count=s['available_deck_findings'];assert count>0
        assert all('ANTENNA' in k for k in s['available_deck_findings_by_category'])
        assert p['fresh_DRC_count']==0 and p['whole_signal_geometry']['pass']
        assert (p['separate_diode_cost']['inserted_real_ANTENNA_X1'] if source_kind=='diode' else p['retained_real_diode_count'])==636
        rdb=stream/'diagnostic.lyrdb';native=physical/'whole_access.tsv.gz'
        assert sha(rdb)==s['files'][rdb.name]['sha256'] and sha(native)==p['files'][native.name]['sha256']
        initial=ROOT/'antenna_netmap/r02';initial_p=json.loads((initial/'execution.json').read_text())
        existing=initial/'unique_correlated_native_nets.json'
        assert initial_p['native_returncode']==0 and initial_p['all_sources_unchanged']
        assert sha(existing)==initial_p['files'][existing.name]['sha256']
        assert len(set(json.loads(existing.read_text())))==636
        spec={'RDB':str(rdb),'native_conductors':str(native),'top':'gemm_engine','expected_findings':count,
          'existing_real_diode_nets':str(existing),
          'standard_GDS':'/OpenROAD-flow-scripts/flow/platforms/nangate45/gds/NangateOpenCellLibrary.gds',
          'deck':'/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc'}
        inputs={str(q):sha(q) for q in [sp,pp,physical/'routed.def',rdb,native,initial/'execution.json',existing]}
        rec['source_SHA']=inputs
        (out/'input.json').write_text(json.dumps(spec,indent=2)+'\n')
        command=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
          '--home',str(ROOT/'home'),'--pwd',str(out),'--env','PINXY_ANTENNA_MAP_OUT='+str(out),
          IMAGE,'klayout','-b','-r',str(DRIVER/'map_antenna_polygons.py')]
        with (out/'native.log').open('x') as f:rec['native_returncode']=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT).returncode
        if (out/'correlation_summary.json').exists():rec['correlation_summary']=json.loads((out/'correlation_summary.json').read_text())
        rec['all_sources_unchanged']=all(sha(Path(k))==v for k,v in inputs.items())
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={q.name:{'bytes':q.stat().st_size,'sha256':sha(q)} for q in out.iterdir() if q.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return 0 if rec.get('native_returncode')==0 and rec.get('all_sources_unchanged') else 1


if __name__=='__main__':sys.exit(run(*sys.argv[1:3]))
