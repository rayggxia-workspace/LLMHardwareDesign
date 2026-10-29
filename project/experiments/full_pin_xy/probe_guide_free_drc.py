"""Compare full native DRC with/without search-guide metadata on a real failure.

Never drop physical obstacles, wires, vias, pins, NDRs or rules. Original and
metadata-only copies run the identical DRC command in independent processes.
This probe is not accelerator or whole-leaf qualification.
"""
from pathlib import Path
import datetime,gzip,json,os,re,subprocess,sys,time,traceback
from run_exports import ROOT,IMAGE,BIN,sha
from run_parent_trial import tcl
from run_escape_fixture import execute

DRIVER=Path(__file__).resolve().parent


def run(revision,profile='adapter'):
    assert profile in ['adapter','owned_cap_stage'];leaf=profile=='owned_cap_stage'
    source=ROOT/('llsys_owned_cap_access/r01' if leaf else 'upper_branch_neighbors/r01/llaccel')
    rp=source/'execution.json';raw_receipt=rp.read_bytes();q=json.loads(raw_receipt)
    if leaf:
        assert q['native_returncodes']['actual_edit_and_geometry_export']==0
        assert q['complete_pin_contract']['all_signal_pins']==13507 and len(q['complete_pin_contract']['only_changed_XY_pins'])==10261
        assert all(q['all_original_cells_signal_connections_PG_die_unchanged'].values())
        odb=source/'routed.odb';proof=ROOT/'guide_free_DRC_probe/r02/execution.json';pq=json.loads(proof.read_text())
        assert pq.get('completed_utc') and pq['original_guide_count']==11115 and pq['remaining_guide_count']==0 and pq['all_native_DRC_markers_byteexact']
        assert pq['original_native_DRC_count']==pq['guide_free_native_DRC_count']==2 and pq['all_closed_sources_unchanged']
        stable=[odb,proof,source/'whole_access.tsv.gz',source/'fresh.tcl']+[source/('after.'+k+'.tsv') for k in ['pins','cells','pdn','die']]
        if q.get('completed_utc'):stable+=[rp,source/'independent.log',source/'independent.drc']
        expected_fresh='read_db '+tcl(odb)+'\nset_routing_layers -signal metal2-metal8 -clock metal4-metal8\ndrt::check_drc -output_file '+tcl(source/'independent.drc')+'\n'
        assert (source/'fresh.tcl').read_text()==expected_fresh
        routing='set_routing_layers -signal metal2-metal8 -clock metal4-metal8'
    else:
        assert q.get('completed_utc') and q['all_closed_sources_unchanged'] and q['fresh_DRC_count']==2
        odb=source/'routed_770_BRANCHES_NOT_SYSTEM.odb';assert sha(odb)==q['files'][odb.name]['sha256']
        stable=[rp,odb];routing='set_routing_layers -signal metal11-metal12 -clock metal11-metal12'
    inputs={str(p):sha(p) for p in stable}
    out=ROOT/('guide_free_leaf_DRC' if leaf else 'guide_free_DRC_probe')/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'CURRENT10261_PIN_LEAF_FULL_NATIVE_DRC_METADATA_CONTROL_NOT_RC_STA_PARENT_OR_FULL_QUALIFICATION' if leaf else 'REAL_ALL770_ADAPTER_BRANCH_NATIVE_DRC_GUIDE_METADATA_CONTROL_NOT_ACCELERATOR_QUALIFICATION',
         'source_SHA':inputs,'full_qualification':False,'profile':profile,
         'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
         'native_returncodes':{},'routing_layers_signal_and_clock':routing,
         'all_original_checks_retained':True,'metadata_policy':'Only dbGuide objects on a new copy; no routing/DRC command or physical geometry is removed'}
    save=lambda:(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');save()
    if leaf:
        name='original_case_receipt.json' if q.get('completed_utc') else 'original_case_observation_NOT_TERMINAL.json'
        (out/name).write_bytes(raw_receipt)
        rec['source_case_receipt_state']='TERMINAL' if q.get('completed_utc') else 'ACTIVE_CLOSED_EDIT_STAGE_ONLY'
        rec['source_case_snapshot_not_used_as_immutable_input']=not bool(q.get('completed_utc'))
        rec['original_guided_fresh_DRC_not_reexecuted']='Original job93343 is never resubmitted; only an already completed native gate is eligible for the comparison below'
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    try:
        rec['actual_OpenROAD_binary_SHA256']=subprocess.check_output(common+[IMAGE,'sha256sum',BIN]).decode().split()[0]
        assert rec['actual_OpenROAD_binary_SHA256']==q['actual_OpenROAD_binary_SHA256']
        helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
        contracts=(DRIVER/'output_chain_placement.tcl').read_text().split('read_db $::env(PINXY_CHAIN_SOURCE)',1)[0]
        body='''set b [ord::get_db_block]
puts "ACTUAL_GUIDE_DESTRUCTION_COMMANDS [info commands ::odb::*Guide*destroy*]"
if {![llength [info commands ::odb::dbGuide_destroy]]} {error "Installed native guide destruction unavailable; no unsupported mutation"}
fingerprint BEFORE
set original_obs [obs_snapshot]
set ::env(PINXY_ACCESS_ALL) 1
set ::env(PINXY_ACCESS_OUT) BEFORE_ACCESS
source EXPORTER
set native_guide_count_before 0;foreach n [$b getNets] {incr native_guide_count_before [llength [$n getGuides]]}
if {$native_guide_count_before<=0} {error "Actual source has no guides; this would be a vacuous probe"}
foreach n [$b getNets] {set guides [$n getGuides];foreach g $guides {odb::dbGuide_destroy $g}}
set native_guide_count_after 0;foreach n [$b getNets] {incr native_guide_count_after [llength [$n getGuides]]}
if {$native_guide_count_after!=0 || [obs_snapshot] ne $original_obs} {error "Guide metadata removal or OBS preservation failed"}
fingerprint AFTER
set ::env(PINXY_ACCESS_OUT) AFTER_ACCESS
source EXPORTER
set f [open COUNTS w];puts $f "$native_guide_count_before\t$native_guide_count_after";close $f
write_db NEWODB
close $stages
'''
        for key,value in [('BEFORE_ACCESS',out/'before_access.tsv.gz'),('AFTER_ACCESS',out/'after_access.tsv.gz'),('BEFORE',out/'before'),('AFTER',out/'after'),('EXPORTER',DRIVER/'export_access.tcl'),('COUNTS',out/'actual_guide_counts.tsv'),('NEWODB',out/'guide_metadata_removed_NOT_QUALIFIED.odb')]:body=body.replace(key,tcl(value))
        if leaf:
            # Reuse only immutable, already completed native edit-stage exports.
            # Do not rewrite the running source or repeat its complete exports.
            body=body.replace('fingerprint '+tcl(out/'before')+'\n','')
            body=body.replace('set ::env(PINXY_ACCESS_OUT) '+tcl(out/'before_access.tsv.gz')+'\nsource '+tcl(DRIVER/'export_access.tcl')+'\n','')
        script=out/'remove_metadata_only.tcl';script.write_text(helper+'\n'+contracts+'\nread_db '+tcl(odb)+'\n'+body)
        rec['native_returncodes']['metadata_copy_and_physical_exports']=execute(common,script,out/'metadata.log','PINXY_OUTPUT='+str(out),threads=1)
        assert rec['native_returncodes']['metadata_copy_and_physical_exports']==0
        count,remaining=map(int,(out/'actual_guide_counts.tsv').read_text().split());assert count>0 and remaining==0
        rec['original_guide_count']=count;rec['remaining_guide_count']=remaining
        rec['all_native_physical_fingerprints_unchanged']={k:sha(source/('after.'+k+'.tsv') if leaf else out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['pins','cells','pdn','die']}
        assert all(rec['all_native_physical_fingerprints_unchanged'].values())
        before_geometry=source/'whole_access.tsv.gz' if leaf else out/'before_access.tsv.gz'
        assert sha(before_geometry)==sha(out/'after_access.tsv.gz'),'Deterministic native gzip physical export changed'
        rec['all_source_native_WIRE_VIA_terminal_exports_byteexact']=True
        if not leaf:rec['all770_native_WIRE_VIA_terminal_exports_byteexact']=True
        rec['all_original_OBS_preserved']=True;save()
        variants=[('guide_free',out/'guide_metadata_removed_NOT_QUALIFIED.odb')] if leaf else [('original',odb),('guide_free',out/'guide_metadata_removed_NOT_QUALIFIED.odb')]
        for label,path in variants:
            script=out/(label+'_fresh.tcl');script.write_text('read_db '+tcl(path)+'\n'+routing+'\ndrt::check_drc -output_file '+tcl(out/(label+'.drc'))+'\n')
            start=time.monotonic();rec['native_returncodes'][label+'_fresh_DRC']=execute(common,script,out/(label+'.log'),threads=1)
            rec[label+'_fresh_elapsed_seconds']=time.monotonic()-start;save()
            assert rec['native_returncodes'][label+'_fresh_DRC']==0
            rec[label+'_native_DRC_count']=len(re.findall(r'^violation type:',(out/(label+'.drc')).read_text(),re.M))
            guide_counts=re.findall(r'Number of guides:\s*(\d+)',(out/(label+'.log')).read_text())
            assert guide_counts==[str(count if label=='original' else remaining)],'Independent native guide inventory differs from metadata count'
        if leaf:
            rec['probe_outcome']='GUIDE_FREE_FULL_NATIVE_RESULT_ONLY; original guided check still separate; no RC_STA_parent_or_full_qualification'
            # Never compare against an incompletely written original DRC file.
            current=json.loads(rp.read_text())
            if current.get('native_returncodes',{}).get('fresh_DRC')==0:
                rec['original_guided_fresh_native_DRC_count']=current['fresh_DRC_count']
                guided_counts=re.findall(r'Number of guides:\s*(\d+)',(source/'independent.log').read_text())
                assert guided_counts==[str(count)],'Original full native guide count differs from metadata inventory'
                rec['original_guided_completed_markers_byteexact']=(source/'independent.drc').read_bytes()==(out/'guide_free.drc').read_bytes()
                assert rec['original_guided_completed_markers_byteexact'],'Actual full guided/free native results differ; do not promote the new method'
        else:
            rec['all_native_DRC_markers_byteexact']=(out/'original.drc').read_bytes()==(out/'guide_free.drc').read_bytes()
            assert rec['all_native_DRC_markers_byteexact'] and rec['original_native_DRC_count']>0
            rec['probe_outcome']='SAME_REAL_FAILURE_WITH_FULL_NATIVE_COMMAND_AND_PHYSICAL_EXPORTS_NOT_FULL_LEAF_OR_SYSTEM_PROOF'
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==s for p,s in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    return 0 if not rec.get('actual_failure') and rec['all_closed_sources_unchanged'] and (not leaf or rec.get('guide_free_native_DRC_count')==0) else 1


if __name__=='__main__':sys.exit(run(*sys.argv[1:]))
