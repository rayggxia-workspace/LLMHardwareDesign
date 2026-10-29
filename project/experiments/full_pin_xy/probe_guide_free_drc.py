"""Compare full native DRC with/without search-guide metadata on a real failure.

Never drop physical obstacles, wires, vias, pins, NDRs or rules. Original and
metadata-only copies run the identical DRC command in independent processes.
This probe is not accelerator or whole-leaf qualification.
"""
from pathlib import Path
import datetime,gzip,json,os,re,sys,time,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute

DRIVER=Path(__file__).resolve().parent


def run(revision):
    source=ROOT/'upper_branch_neighbors/r01/llaccel';rp=source/'execution.json';q=json.loads(rp.read_text())
    assert q.get('completed_utc') and q['all_closed_sources_unchanged'] and q['fresh_DRC_count']==2
    odb=source/'routed_770_BRANCHES_NOT_SYSTEM.odb';assert sha(odb)==q['files'][odb.name]['sha256']
    inputs={str(p):sha(p) for p in [rp,odb]}
    out=ROOT/'guide_free_DRC_probe'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'REAL_ALL770_ADAPTER_BRANCH_NATIVE_DRC_GUIDE_METADATA_CONTROL_NOT_ACCELERATOR_QUALIFICATION',
         'source_SHA':inputs,'full_qualification':False,'source_composed_fresh_DRC_count':2,
         'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
         'native_returncodes':{},'routing_layers_signal_and_clock':'metal11-metal12_UNCHANGED',
         'all_original_checks_retained':True,'metadata_policy':'Only dbGuide objects on a new copy; no routing/DRC command or physical geometry is removed'}
    save=lambda:(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');save()
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    try:
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
set count 0;foreach n [$b getNets] {incr count [llength [$n getGuides]]}
if {$count<=0} {error "Actual source has no guides; this would be a vacuous probe"}
foreach n [$b getNets] {set guides [$n getGuides];foreach g $guides {odb::dbGuide_destroy $g}}
set remaining 0;foreach n [$b getNets] {incr remaining [llength [$n getGuides]]}
if {$remaining!=0 || [obs_snapshot] ne $original_obs} {error "Guide metadata removal or OBS preservation failed"}
fingerprint AFTER
set ::env(PINXY_ACCESS_OUT) AFTER_ACCESS
source EXPORTER
set f [open COUNTS w];puts $f "$count\t$remaining";close $f
write_db NEWODB
close $stages
'''
        for key,value in [('BEFORE_ACCESS',out/'before_access.tsv.gz'),('AFTER_ACCESS',out/'after_access.tsv.gz'),('BEFORE',out/'before'),('AFTER',out/'after'),('EXPORTER',DRIVER/'export_access.tcl'),('COUNTS',out/'actual_guide_counts.tsv'),('NEWODB',out/'guide_metadata_removed_NOT_QUALIFIED.odb')]:body=body.replace(key,tcl(value))
        script=out/'remove_metadata_only.tcl';script.write_text(helper+'\n'+contracts+'\nread_db '+tcl(odb)+'\n'+body)
        rec['native_returncodes']['metadata_copy_and_physical_exports']=execute(common,script,out/'metadata.log','PINXY_OUTPUT='+str(out),threads=1)
        assert rec['native_returncodes']['metadata_copy_and_physical_exports']==0
        count,remaining=map(int,(out/'actual_guide_counts.tsv').read_text().split());assert count>0 and remaining==0
        rec['original_guide_count']=count;rec['remaining_guide_count']=remaining
        rec['all_native_physical_fingerprints_unchanged']={k:sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['pins','cells','pdn','die']}
        assert all(rec['all_native_physical_fingerprints_unchanged'].values())
        assert gzip.decompress((out/'before_access.tsv.gz').read_bytes())==gzip.decompress((out/'after_access.tsv.gz').read_bytes())
        rec['all770_native_WIRE_VIA_terminal_exports_byteexact']=True;rec['all_original_OBS_preserved']=True;save()
        for label,path in [('original',odb),('guide_free',out/'guide_metadata_removed_NOT_QUALIFIED.odb')]:
            script=out/(label+'_fresh.tcl');script.write_text('read_db '+tcl(path)+'\nset_routing_layers -signal metal11-metal12 -clock metal11-metal12\ndrt::check_drc -output_file '+tcl(out/(label+'.drc'))+'\n')
            start=time.monotonic();rec['native_returncodes'][label+'_fresh_DRC']=execute(common,script,out/(label+'.log'),threads=1)
            rec[label+'_fresh_elapsed_seconds']=time.monotonic()-start;save()
            assert rec['native_returncodes'][label+'_fresh_DRC']==0
            rec[label+'_native_DRC_count']=len(re.findall(r'^violation type:',(out/(label+'.drc')).read_text(),re.M))
        rec['all_native_DRC_markers_byteexact']=(out/'original.drc').read_bytes()==(out/'guide_free.drc').read_bytes()
        assert rec['all_native_DRC_markers_byteexact'] and rec['original_native_DRC_count']>0
        rec['probe_outcome']='SAME_REAL_FAILURE_WITH_FULL_NATIVE_COMMAND_AND_PHYSICAL_EXPORTS_NOT_FULL_LEAF_OR_SYSTEM_PROOF'
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==s for p,s in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    return 0 if not rec.get('actual_failure') and rec['all_closed_sources_unchanged'] else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
