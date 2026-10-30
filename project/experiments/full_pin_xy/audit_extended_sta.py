"""Read-only six-leaf clock/electrical coverage audit on exact routed sources.

Extends the existing setup/hold/max-load reports with the check types supported
by this installed STA. No constraints, libraries, parasitics or design change.
An executed empty check report is not proof that a library rule was defined.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import datetime,json,os,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute

DRIVER=Path(__file__).resolve().parent
SOURCES={
 'act':('trials/act-access-r03/act-C','act-access-r03',True),
 'mxu':('pin_escape_route/r02/mxu-C','access-r03',False),
 'opentpu_aux':('system_patch_route/r02/opentpu_aux-C','access-r03',False),
 'gemm':('antenna_incremental_eco/r01/gemm-C','access-r03',False),
 'vector':('vector_resume/r01','access-r03',False),
 'llaccel_aux':('trials/llsys-pg-r03/llaccel_aux-C','llsys-pg-r03',True)}


def one(case,parent):
    relative,rev,legacy=SOURCES[case];source=ROOT/relative
    rp=source/'execution.json';rec0=json.loads(rp.read_text())
    assert rec0.get('finished_utc') if legacy else rec0.get('completed_utc')
    oldpath=ROOT/'trials'/rev/(case+'-C')/'execution.json';old=json.loads(oldpath.read_text())
    odb=source/'routed.odb';spef=source/'extracted.spef';sdc=Path(old['source_sdc'])
    indexed=rec0['outputs' if legacy else 'files']
    for p in [odb,spef]:assert sha(p)==indexed[p.name]['sha256']
    assert sha(sdc)==old['input_sha256'][str(sdc)]
    refs=[source/(('timing.' if legacy else '')+kind+'.txt') for kind in ['setup','hold']]
    for p in refs:assert sha(p)==indexed[p.name]['sha256']
    capability=ROOT/'sta_coverage_api/r01/native.log';log=capability.read_text()
    assert '[-min_pulse_width] [-min_period] [-max_skew]' in log and 'NO_DESIGN_LOADED_NO_CLOCK_OR_TIMING_PASS_INFERRED' in log
    out=parent/case;out.mkdir(exist_ok=False)
    inputs={str(p):sha(p) for p in [rp,oldpath,odb,spef,sdc,capability]+refs}
    rec={'scope':'SOURCE_BOUND_EXTENDED_STA_CHECK_COVERAGE_NOT_FULL_LEAF_OR_SYSTEM_QUALIFICATION',
      'case':case,'actual_source':str(source),'source_SHA':inputs,'original_constraints_and_SPEF_unchanged':True,
      'full_qualification':False,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
      'scheduler_job':os.environ['SLURM_JOB_ID'],'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'clock_min_period_report_scope':'Derived same-edge register path minimum period, not missing Liberty minimum_period characterization',
      'applicability_policy':'Raw actual Liberty inventory and SDC required. Empty/undefined checks are not zero violations or manufacturing qualification.',
      'capability_receipt_limit':'Original native capability log complete; wrapper 93075 subsequently failed NameError while writing its metadata; original failure retained, no repeated probe.'}
    def save():(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    save()
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
      '--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
      '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
      '--home',str(ROOT/'home'),'--pwd',str(out)]
    for p in old['libs']:
        if Path(p).is_file():common+=['--bind',p+':'+p+':ro']
    try:
        lines=['read_liberty '+tcl(p) for p in old['libs']]+['read_db '+tcl(odb),'read_sdc '+tcl(sdc),
          'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl','read_spef '+tcl(spef)]
        lines+=['report_worst_slack -max -digits 6 > '+tcl(out/'setup.txt'),
          'report_worst_slack -min -digits 6 > '+tcl(out/'hold.txt'),
          'report_check_types -min_pulse_width -min_period -max_skew -clock_gating_setup -clock_gating_hold -min_slew -min_capacitance -min_fanout -max_count 1000000 -digits 6 > '+tcl(out/'extended_checks_all_not_only_violators.txt'),
          'report_clock_properties > '+tcl(out/'actual_clock_properties.txt'),
          'report_clock_min_period -include_port_paths > '+tcl(out/'derived_path_min_period_NOT_LIBERTY_RULE.txt'),
          'report_clock_skew -setup -digits 6 > '+tcl(out/'setup_clock_skew.txt'),
          'report_clock_skew -hold -digits 6 > '+tcl(out/'hold_clock_skew.txt'),
          'report_clock_latency -digits 6 > '+tcl(out/'clock_latency.txt'),
          'check_setup -verbose > '+tcl(out/'constraint_coverage.txt'),
          'report_parasitic_annotation -report_unannotated > '+tcl(out/'parasitic_coverage.txt'),
          'set f [open '+tcl(out/'loaded_library_check_definitions.tsv')+' w];puts $f "source\tsha256\ttiming_type\tdeclarations"']
        for p in old['libs']:
            lines+=['set source '+tcl(p)+';set digest [lindex [exec sha256sum $source] 0];set libf [open $source r];set content [read $libf];close $libf',
              r'''foreach name {min_pulse_width minimum_period clock_gating_setup_rising clock_gating_setup_falling clock_gating_hold_rising clock_gating_hold_falling} {set pattern [format {timing_type\s*:\s*%s\s*;} $name];puts $f [join [list $source $digest $name [regexp -all $pattern $content]] "\t"]}''']
        lines+=['close $f','puts {SOURCE_BOUND_EXTENDED_CHECKS_EXECUTED_NOT_FULL_QUALIFICATION}']
        script=out/'audit.tcl';script.write_text('\n'.join(lines)+'\n')
        rec['native_returncode']=execute(common,script,out/'native.log',threads=1)
        rec['source_worst_slacks_exactly_replayed']={kind:(out/(kind+'.txt')).exists() and (out/(kind+'.txt')).read_text()==ref.read_text() for kind,ref in zip(['setup','hold'],refs)}
        checks=out/'extended_checks_all_not_only_violators.txt'
        if checks.exists():rec['extended_literal_VIOLATED_rows_not_complete_rule_coverage']=checks.read_text().count('(VIOLATED)')
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_sources_unchanged']=all(sha(Path(p))==v for p,v in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    return rec


def run(revision):
    assert int(os.environ['SLURM_CPUS_PER_TASK'])>=2
    out=ROOT/'extended_sta'/revision;out.mkdir(parents=True,exist_ok=False)
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda c:one(c,out),SOURCES))
    q={'scope':'ALL_SIX_EXACT_SOURCE_EXTENDED_CHECK_EXECUTION_NOT_FULL_RULE_OR_SYSTEM_PASS','full_qualification':False,
      'records':[{k:r[k] for k in ['case','native_returncode','all_sources_unchanged','source_worst_slacks_exactly_replayed'] if k in r} for r in results],
      'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (out/'execution.json').write_text(json.dumps(q,indent=2)+'\n')
    return 0 if all(r.get('native_returncode')==0 and r.get('all_sources_unchanged') and all(r.get('source_worst_slacks_exactly_replayed',{}).values()) for r in results) else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
