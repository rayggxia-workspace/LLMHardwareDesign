"""Immutable bounded evidence for GDS import/deck and current physical gates."""
from pathlib import Path
import argparse,datetime,gzip,hashlib,json,subprocess,tarfile

ROOT=Path('/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027')
JOBS=['92690','92691','92700','92714','92721','92781','92783','92792','92794','92795','92798','92812','92825','92834','92835','92837','92838','92841','92846','92847','92848','92853','92854','92855','92861','92867','92872','92886','92891','92892','92901','92903','92910','92912','92913','92914','92915','92921','92925','92929','92930','92931','92940','92943']


JOBS+=['92968','92969','92972','92974','92975','92976','92979','92984','92985','92997','93015']
JOBS+=['93025']
JOBS+=['93028','93030','93031']
JOBS+=['93038','93040']
JOBS+=['93041','93043','93048','93049']
JOBS+=['93051']
JOBS+=['93060','93061']
JOBS+=['93072','93073','93074','93075','93076']
JOBS+=['93083']
JOBS+=['93089','93090','93092','93094']
JOBS+=['93102','93106']


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(4*1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def collect(name):
    assert name.replace('-','').isalnum()
    out=ROOT/'gate_milestones'/name;out.mkdir(parents=True,exist_ok=False)
    patterns=['streamout/costed-r0[12]/*/*','streamout/costed-r0[12]/pack.json',
      'tool_api/streamout-reader-r0[123]/*','logs/streamout-reader-api-r0[123]-*.log',
      'logs/costed-gds-r0[12]-*.log','logs/stream-pack-costed-r0[12]-*.log',
      'checkpoint_route/r01/*','trials/access-r03/llaccel_aux-C/execution.json',
      'trials/access-r03/llaccel_aux-C/stages.tsv','finalized/access-r03/llaccel_aux-C/*',
      'escape_fixtures/gemm-r01/*/*','escape_fixtures/gemm-r02/*/*',
      'escape_fixtures/mxu-r01/*/*','leaf_eco/boundary-r01/*/*','logs/boundary-eco-r01-*.log',
      'antenna_audit/r01/*','logs/antenna-audit-r01-*.log','antenna_rules/r01/*',
      'eco_views/r03/opentpu_aux-C/*','mapped_equivalence/r01/*/*','escape_landing/r01/gemm-C/*',
      'inputs/gemm-actual-landing-r01/landing_delta.json','logs/antenna-rules-r01-*.log',
      'logs/sys-eco-view-r03-*.log','logs/mapped-eco-*-r01-*.log','logs/gemm-actual-landing-r01-*.log',
      'eco_views/r04/*/*','leaf_timing_models/r07/*/*','fixed_wire_api/r0[12]/*',
      'common_integration/r01/*/*','estimator_diagnosis/r0[12]/*','logs/common-integration-C-r01-*.log',
      'logs/fixed-wire-api-r0[12]-*.log','logs/estimator-isolate-r0[12]-*.log','logs/integration-model-r07-*.log',
      'tmp/estimator-order-reference-r01.json','vector_resume/r01/*','buffered_equivalence/r01/*/*',
      'parent_region_audit/r01/*','escape_landing/r02/mxu-C/*','inputs/mxu-actual-landing-r02/landing_delta.json',
      'antenna_netmap/r0[12]/*','logs/buffered-proof-r01-*.log','logs/mxu-region-r01-*.log',
      'logs/mxu-actual-landing-r02-*.log','logs/antenna-netmap-r0[12]-*.log','logs/vector-resume-r01-*.log',
      'antenna_diode_eco/r01/gemm-C/*','antenna_diode_stream/r01/gemm-C/*','buffered_equivalence/r01/vector/*',
      'actual_path_audit/r01/*/*','logs/antenna-diode-r01-*.log','logs/antenna-diode-stream-r01-*.log',
      'logs/vector-buffered-proof-r01-*.log','logs/vector-actual-paths-r01-*.log','logs/sys-actual-paths-r01-*.log',
      'output_chain_placement/r01/opentpu_aux-C/*','logs/output-chain-r01-*.log',
      'output_chain_resume/r01/opentpu_aux-C/*','logs/output-chain-resume-r01-*.log',
      'passive_load_equivalence/r01/gemm/*','shared_conductor_audit/r0[12]/*',
      'logs/passive-load-proof-r01-*.log','logs/shared-fixed-audit-r0[12]-*.log',
      'diode_cap_eco/r01/gemm-C/*','antenna_diode_stream/cap-r01/gemm-C/*',
      'logs/diode-cap-eco-r01-*.log','logs/post-cap-gds-r01-*.log',
      'output_chain_resume/r02/opentpu_aux-C/*','logs/system_chain_resume_r02-*.log',
      'upper_adaptation_trial/r0[12]/*','upper_adaptation_trial/r0[12]/*/*','logs/full_upper_adapter_r0[12]-*.log',
      'post_diode_netmap/cap-r01/*','logs/post-diode-map-cap-r01-*.log',
      'antenna_incremental_eco/r01/gemm-C/*','antenna_diode_stream/incremental-r01/gemm-C/*',
      'route_representation_audit/r01/*','tool_api/grt-start-r0[12]/*',
      'logs/incremental_diode_eco_r01-*.log','logs/incremental_diode_gds_r01-*.log',
      'logs/route-box-r01-*.log','logs/grt-capability-r0[12]-*.log',
      'diode_views/r01/gemm-C/*','logs/real-diode-view-r01-*.log',
      'upper_tool_diagnosis/r01/*','logs/upper-fullframe-diagnostic-r01-*.log',
      'upper_detailed_resume/r01/*','upper_detailed_resume/r01/*/*','logs/upper-detailed-r01-*.log',
      'actual_path_audit/r02/*/*','logs/system-relocated-path-r02-*.log',
      'upper_search_budget/r01/*','upper_search_budget/r01/*/*','logs/upper-search-r01-*.log',
      'system_patch_route/r0[12]/*/*','logs/system-patch-r0[12]-*.log',
      'pin_escape_route/r0[12]/*/*','logs/mxu-escape-r0[12]-*.log',
      'escape_fixtures/gemm658-r0[12]/*/*','logs/gemm658-parent-r0[12]-*.log',
      'vector_clone_probe/r01/*','logs/vector-clone-probe-r01-*.log',
      'vector_clone_crash/r0[12]/*','logs/vector-crash-r0[12]-*.log',
      'pin_escape_views/r01/*/*','logs/mxu-pin-escape-views-r01-*.log',
      'system_stacked_via_route/r01/*/*','logs/system-stacked-via-r01-*.log',
      'vector_clone_probe/r02/*','logs/vector-clone-probe-r02-*.log',
      'escape_view_recheck/r01/*/*','logs/mxu-escape-view-recheck-r01-*.log',
      'sta_coverage_api/r01/*','logs/sta-coverage-api-r01-*.log',
      'extended_sta/r01/*','extended_sta/r01/*/*','logs/extended-sta-r01-*.log']
    patterns+=['vector_clone_probe/r03/*','logs/vector-clone-probe-r03-*.log']
    patterns+=['system_stacked_via_views/r01/*/*','logs/system-stacked-views-r01-*.log',
      'upper_grid_phase/r01/*','upper_grid_phase/r01/*/*','logs/upper-grid-phase-r01-*.log',
      'llsys_DRC_diagnosis/r01/*','logs/llsys-drc-diagnosis-r01-*.log',
      'vector_probe_equivalence/r01/*','logs/vector-probe-proof-r01-*.log']
    patterns+=['vector_probe_partition_diagnosis/r01/*','logs/vector-partition-diagnosis-r01-*.log',
      'vector_partition_restore/r01/*','logs/vector-partition-restore-r01-*.log',
      'vector_probe_route/r01/*','logs/vector-probe-route-r01-*.log']
    stable_intermediates={}
    incremental=ROOT/'antenna_incremental_eco/r01/gemm-C/execution.json'
    if incremental.exists() and json.loads(incremental.read_text()).get('native_returncodes',{}).get('implementation')==0:
        for filename in ['routed.odb','routed.def','extracted.spef','whole_access.tsv.gz','before.original.tsv','after.original.tsv']:
            stable_intermediates[str(incremental.parent/filename)]='incremental_diode_native_implementation'
    vector=ROOT/'vector_resume/r01/execution.json'
    if vector.exists():
        q=json.loads(vector.read_text())
        for stage,filename in [('timing_repair','timing_repaired_NOT_LEGALIZED_OR_ROUTED.odb'),('legalization','placed_NOT_ROUTED.odb')]:
            if q.get('native_returncodes',{}).get(stage)==0:stable_intermediates[str(vector.parent/filename)]=stage
    resumed=ROOT/'output_chain_resume/r01/opentpu_aux-C/execution.json'
    if resumed.exists() and json.loads(resumed.read_text()).get('native_returncodes',{}).get('legalization')==0:
        for stage_file in ['placed_NOT_ROUTED.odb','placed.connections.tsv','placed.nonselected.tsv']:
            stable_intermediates[str(resumed.parent/stage_file)]='isolated_legalization'
    records=[]
    for p in sorted(set(p for pattern in patterns for p in ROOT.glob(pattern) if p.is_file())):
        a=p.stat();r={'source':str(p),'bytes':a.st_size}
        keep=p.suffix in ['.json','.log','.tcl','.txt','.tsv','.csv','.drc','.lyt'] and a.st_size<=8*1024*1024
        if 'upper_adaptation_trial/r02/' in str(p) and p.name=='congestion.rpt' and a.st_size<=8*1024*1024:keep=True
        if 'antenna_diode_stream/' in str(p) and p.suffix=='.lyrdb' and a.st_size<=8*1024*1024:keep=True
        if 'upper_tool_diagnosis/r01/' in str(p) and p.suffix=='.guide' and a.st_size<=8*1024*1024:keep=True
        if 'antenna_rules/r01' in str(p) and p.suffix in ['.lef','.lydrc'] and a.st_size<=8*1024*1024:keep=True
        if 'fixed_wire_api' in str(p) and p.suffix=='.def' and a.st_size<=1024*1024:keep=True
        if 'actual_path_audit/' in str(p) and p.name=='fresh_DRC_target_net.tsv.gz' and a.st_size<=8*1024*1024:keep=True
        if 'pin_escape_views/' in str(p) and p.name=='target_pin_access.tsv.gz' and a.st_size<=8*1024*1024:keep=True
        if 'extended_sta/r01/' in str(p) and p.name=='extended_checks_all_not_only_violators.txt' and a.st_size<=64*1024*1024:keep=True
        if 'system_stacked_via_views/' in str(p) and p.name in ['before_actual_target.tsv.gz','after_actual_target.tsv.gz','current_source_extended_checks_all.txt'] and a.st_size<=64*1024*1024:keep=True
        omit_paths='paths.json' in p.name and 'actual_path_audit/' not in str(p)
        keep=keep and not omit_paths and not any(s in p.name for s in ['.cells.','.pdn.','whole_access.tsv','selected_access.tsv'])
        if not keep:
            r['storage']='REMOTE_ONLY_INDEXED'
            if str(p) in stable_intermediates:
                digest=sha(p);b=p.stat()
                if (a.st_size,a.st_mtime_ns)==(b.st_size,b.st_mtime_ns):r.update({'storage':'REMOTE_ONLY_COMPLETED_NATIVE_STAGE_SHA256','sha256':digest,'closed_native_stage':stable_intermediates[str(p)]})
            # Finished execution receipts already index their large output SHA;
            # don't hash a live multi-GB ODB/GDS or copy it into Git.
            records.append(r);continue
        raw=p.read_bytes();b=p.stat()
        if (a.st_size,a.st_mtime_ns)!=(b.st_size,b.st_mtime_ns):
            r['storage']='CHANGING_ACTIVE_FILE_OMITTED';records.append(r);continue
        rel=p.relative_to(ROOT).as_posix()+'.gz';q=out/rel;q.parent.mkdir(parents=True,exist_ok=True)
        with q.open('xb') as f,gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as z:z.write(raw)
        r.update({'storage':'LOSSLESS_SNAPSHOT','relative':rel,'sha256':hashlib.sha256(raw).hexdigest(),'stored_sha256':sha(q)})
        records.append(r)
    scheduler=subprocess.check_output(['sacct','-j',','.join(JOBS),'--parsable2','--format=JobIDRaw,JobName,State,Elapsed,ExitCode']).decode()
    (out/'scheduler.tsv').write_text(scheduler)
    meta={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_root':str(ROOT),
      'scope':'GATE_EVIDENCE_NOT_FULL_PHYSICAL_QUALIFICATION','full_qualification':False,
      'records':records,'running_snapshot_not_terminal_evidence':True}
    (out/'snapshot.json').write_text(json.dumps(meta,indent=2)+'\n')
    with tarfile.open(str(out)+'.tar.gz','x:gz') as f:f.add(str(out),arcname=name)
    print('GATE_MILESTONE',str(out)+'.tar.gz',len(records),'indexed files')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('name');a=p.parse_args();collect(a.name)
