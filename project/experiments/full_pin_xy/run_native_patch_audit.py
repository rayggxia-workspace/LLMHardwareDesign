"""Read-only source-bound RECT inventories and additive connectivity rechecks."""
from pathlib import Path
from collections import Counter
import csv,datetime,gzip,itertools,json,os,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,BIN,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from check_access import check_rows
DRIVER=Path(__file__).resolve().parent
CASES=[
 ('act','finalized/act-access-r03/act-C','clean.odb','whole_access.tsv.gz','whole_access'),
 ('mxu','mxu_actual_via_tip/r01','routed.odb','whole_access.tsv.gz','whole_signal_geometry'),
 ('opentpu_aux','system_stacked_via_route/r01/opentpu_aux-C','routed.odb','whole_access.tsv.gz','whole_signal_geometry'),
 ('gemm','diode_cap_eco/r01/gemm-C','routed.odb','whole_access.tsv.gz','whole_signal_geometry'),
 ('vector','vector_resume/r01','routed.odb','whole_access.tsv.gz','whole_signal_geometry'),
 ('llaccel_stable','llsys_actual_via_tips/r02','routed.odb','whole_access.tsv.gz','whole_signal_geometry'),
 ('llaccel_10261_restored','owned_cap_wire_restore/r01','routed.odb','whole_access.tsv.gz','whole_signal_geometry'),
 ('mxu_parent','mxu_actual_tip_parent/r01/mxu-C','upgraded_parent_NOT_SYSTEM.odb','whole_access.tsv.gz','whole_parent_signal_geometry'),
 ('upper770','upper_branch_repair/r02/llaccel','routed_770_BRANCHES_NOT_SYSTEM.odb','branch_access.tsv.gz','all_770_branch_geometry'),
 ('upper514','upper_branch_repair/r02/llaccel','routed_adapter_NOT_SYSTEM.odb','whole_access.tsv.gz','all_514_composed_geometry'),
 ('gemm_658_current','antenna_incremental_eco/r01/gemm-C','routed.odb','whole_access.tsv.gz','whole_signal_geometry'),
 ('llaccel_13093','llsys_wire_pin_retention/r01','routed.odb','whole_access.tsv.gz','whole_signal_geometry')]

def run(revision,index):
    case,relative,odbname,oldname,graphkey=CASES[index]
    source=ROOT/relative;rp=source/'execution.json';q=json.loads(rp.read_text());odb=source/odbname;old=source/oldname
    source_inputs=[rp,odb,old]
    if case=='act':
        trial=ROOT/'trials/act-access-r03/act-C/execution.json';trialq=json.loads(trial.read_text())
        assert trialq.get('finished_utc') and trialq['returncode']==0 and q['clean_byte_identical_to_pre_RCX_source'] and q['independent_DRC_count']==0
        source_inputs.append(trial)
    else:assert q.get('completed_utc') and q.get('all_closed_sources_unchanged',True)
    for p in [odb,old]:assert sha(p)==q['files'][p.name]['sha256']
    proof=ROOT/'wire_shape_coverage_API/r08/execution.json';proofq=json.loads(proof.read_text())
    assert proofq.get('completed_utc') and proofq['known_probe_exact_patch_verified'] and proofq['native_returncode']==0 and proofq['all_closed_sources_unchanged']
    validated_exporter=ROOT/'drivers/native-patch-export-r08/export_patch_rects.tcl'
    assert sha(DRIVER/'export_patch_rects.tcl')==sha(validated_exporter)
    source_inputs.extend([proof,validated_exporter,DRIVER/'export_patch_rects.tcl']);inputs={str(p):sha(p) for p in source_inputs}
    out=ROOT/'native_patch_audit'/revision/case;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'READ_ONLY_ALL_NATIVE_DBWIRE_RECT_PATCH_INVENTORY_ADDITIVE_EXPORTED_SIGNAL_CONNECTIVITY_NOT_DRC_RC_STA_OR_FULL_QUALIFICATION','case':case,'source_SHA':inputs,'full_qualification':False,'native_route_edit_DRC_RC_STA':'NOT_EXECUTED_READ_ONLY_AUDIT','source_physical_DRC_not_changed_or_promoted':q.get('fresh_DRC_count',q.get('independent_DRC_count')),'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],'array_task':index,'original_special_PG_OBS_and_complete_rules':'SEPARATE_EXISTING_GATES_NOT_REPLACED','legacy_ACT_closure':'Original terminal trial plus independently indexed clean preRCX source; no invented completion field' if case=='act' else None}
    try:
        common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
        rec['actual_OpenROAD_binary_SHA256']=subprocess.check_output(common+[IMAGE,'sha256sum',BIN]).decode().split()[0]
        assert rec['actual_OpenROAD_binary_SHA256']==proofq['actual_OpenROAD_binary_SHA256']
        script=out/'audit.tcl';script.write_text('read_db '+tcl(odb)+'\nif {[[ord::get_db_block] getDbUnitsPerMicron]!=2000} {error \"Source units differ from verified model\"}\nset ::env(PINXY_PATCH_OUT) '+tcl(out/'patch_rectangles.tsv')+'\nset ::env(PINXY_PATCH_COUNTS) '+tcl(out/'patch_counts.tsv')+'\nsource '+tcl(DRIVER/'export_patch_rects.tcl')+'\n')
        rec['native_returncode']=execute(common,script,out/'native.log',threads=1);assert rec['native_returncode']==0
        rec['native_counts']={p[0]:int(p[1]) for p in (line.split('\t') for line in (out/'patch_counts.tsv').read_text().splitlines())}
        assert rec['native_counts']['native_decoder_RECT']==rec['native_counts']['exported_patch_rectangles']
        patch={}
        with (out/'patch_rectangles.tsv').open() as f:
            for r in csv.DictReader(f,delimiter='\t'):patch.setdefault(r['net'],[]).append(r)
        rec['patch_nets']=len(patch);rec['patch_layers']=dict(Counter(r['layer'] for group in patch.values() for r in group))
        baseline=q[graphkey];assert baseline['pass']
        if patch:
            unmatched=set(patch);matched=[]
            def augmented():
                with gzip.open(old,'rt') as f:
                    for name,group in itertools.groupby(csv.DictReader(f,delimiter='\t'),key=lambda r:r['net']):
                        yield from group
                        if name in patch:
                            matched.append(name);unmatched.remove(name)
                            for row in patch[name]:yield dict(row)
            rec['additive_signal_geometry']=check_rows(augmented(),True)
            rec['patch_nets_matched_to_original_multi_terminal_signal_scope']=len(matched)
            rec['patch_nets_outside_original_signal_scope']=sorted(unmatched)
            assert rec['additive_signal_geometry']['checked_nets']==baseline['checked_nets']
            assert rec['additive_signal_geometry']['checked_terminals']==baseline['checked_terminals']
            rec['additive_geometry_pass']=rec['additive_signal_geometry']['pass']
        else:
            rec['additive_geometry_pass']=baseline['pass'];rec['baseline_geometry_reused']='No native RECT events found; original exported graph unchanged, not rerun'
            rec['baseline_geometry_checked_nets']=baseline['checked_nets']
        rec['signal_special_wire_coverage_complete']=rec['native_counts']['signal_special_wire_nets_not_audited']==0
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==v for p,v in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return 0 if not rec.get('actual_failure') and rec['all_closed_sources_unchanged'] and rec.get('signal_special_wire_coverage_complete') and rec.get('additive_geometry_pass') else 1
if __name__=='__main__':sys.exit(run(sys.argv[1],int(os.environ['SLURM_ARRAY_TASK_ID'])))
