"""Reuse failed SYSTEM moves; isolate geometry legalization from STA observers."""
from pathlib import Path
import csv,datetime,json,os,re,shutil,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from check_access import check

DRIVER=Path(__file__).resolve().parent


def run(revision):
    failed=ROOT/'output_chain_placement/r01/opentpu_aux-C';fp=failed/'execution.json';f=json.loads(fp.read_text())
    assert f.get('completed_utc') and f['native_returncodes']['implementation']==-11 and f['all_sources_unchanged']
    checkpoint=failed/'moved_NOT_LEGALIZED_OR_ROUTED.odb'
    assert sha(checkpoint)==f['files'][checkpoint.name]['sha256']
    original=ROOT/'checkpoint_route/r01/routed.odb';assert sha(original)==f['source_SHA'][str(original)]
    old=json.loads((ROOT/'trials/access-r03/opentpu_aux-C/execution.json').read_text());sdc=Path(old['source_sdc'])
    reservations=[Path(k) for k in f['source_SHA'] if k.endswith('/access_reservations.tcl')];assert len(reservations)==1
    for q in [sdc,reservations[0]]:assert sha(q)==f['source_SHA'][str(q)]
    out=ROOT/'output_chain_resume'/revision/'opentpu_aux-C';out.mkdir(parents=True,exist_ok=False)
    inputs={str(p):sha(p) for p in [fp,checkpoint,original,sdc,reservations[0]]}
    for name in ['before.connections.tsv','before.nonselected.tsv','before.pins.tsv','before.pdn.tsv','before.die.tsv','proposed_existing_buffer_moves.tsv']:
        q=failed/name;assert sha(q)==f['files'][name]['sha256'];inputs[str(q)]=sha(q);shutil.copyfile(str(q),str(out/name))
    with (out/'proposed_existing_buffer_moves.tsv').open() as h:moves=list(csv.DictReader(h,delimiter='\t'))
    assert len(moves)==1262 and len({r['instance'] for r in moves})==1262
    selection='set selected_buffers [dict create]\n'+''.join('dict set selected_buffers '+tcl(r['instance'])+' {}\n' for r in moves)
    helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
    code=(DRIVER/'output_chain_placement.tcl').read_text();contracts=code.split('read_db $::env(PINXY_CHAIN_SOURCE)',1)[0]
    tail='set temporary_obs {};'+code.split('set temporary_obs {};',1)[1]
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
      '--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
      '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
      '--home',str(ROOT/'home'),'--pwd',str(out)]
    for path in old['libs']:
        if Path(path).is_file():common+=['--bind',path+':'+path+':ro']
    rec={'scope':'EXISTING_BUFFER_MOVE_CHECKPOINT_RESUME_NOT_NEW_SELECTION_OR_QUALIFICATION',
      'source_SHA':inputs,'full_qualification':False,'selection_or_moves_recomputed':False,
      'original_allowed_layers':'signal M2-M8; clock M4-M8','original_SDC_unchanged':True,
      'hypothesis':'Separate geometry legalization from STA observers; exact crash root cause not established',
      'native_returncodes':{},'scheduler_job':os.environ['SLURM_JOB_ID'],
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    def save():(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    def native(label,lines,env=None):
        script=out/(label+'.tcl');script.write_text('\n'.join(lines)+'\n')
        rc=execute(common,script,out/(label+'.log'),env,threads=4)
        rec['native_returncodes'][label]=rc;save()
        if rc:raise RuntimeError(label+' actual native failure '+str(rc))
    save()
    try:
        native('original_status_export',['read_db '+tcl(original),
          'set f [open '+tcl(out/'original_status.tcl')+' w];puts $f {set original_status [dict create]};set fillers {}',
          'foreach i [[ord::get_db_block] getInsts] {if {[[$i getMaster] getType] eq "CORE_SPACER"} {lappend fillers [[$i getMaster] getName]} else {puts $f [list dict set original_status [$i getName] [$i getPlacementStatus]]}};puts $f [list set filler_masters [lsort -unique $fillers]];close $f'])
        isolated=helper.replace('$out/stages.tsv','$out/legalization.stages.tsv')
        native('legalization',[isolated,contracts,selection,'read_db '+tcl(checkpoint),'set b [ord::get_db_block]',
          'source '+tcl(out/'original_status.tcl'),
          'if {![stage isolated_legalization_no_STA {detailed_placement -use_diamond_legalizer}]} {close $stages;exit 1}',
          'dict for {name status} $original_status {set i [$b findInst $name];if {$i eq "NULL"} {error "Missing original instance"};$i setPlacementStatus $status}',
          'if {![stage check_and_restore_fillers {check_placement -verbose;if {[llength $filler_masters]} {filler_placement -prefix PINXY_CHAIN_ISO_FILL_ $filler_masters} else {puts "ORIGINAL_HAS_NO_CORE_SPACERS_NONE_ADDED"};global_connect;check_placement -verbose}]} {close $stages;exit 1}',
          'connection_contract '+tcl(out/'placed.connections.tsv'),'nonselected_pose_contract '+tcl(out/'placed.nonselected.tsv'),
          'write_db '+tcl(out/'placed_NOT_ROUTED.odb'),'close $stages'],'PINXY_OUTPUT='+str(out))
        for kind in ['connections','nonselected']:
            assert sha(out/('placed.'+kind+'.tsv'))==sha(out/('before.'+kind+'.tsv'))
        rec['isolated_geometry_contracts_pass']=True;save()
        lines=[helper.replace('$out/stages.tsv','$out/route.stages.tsv'),contracts,selection]+['read_liberty '+tcl(p) for p in old['libs']]
        lines+=['read_db '+tcl(out/'placed_NOT_ROUTED.odb'),'read_sdc '+tcl(sdc),
          'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl',
          'set b [ord::get_db_block];set u [$b getDbUnitsPerMicron];set original_obs [obs_snapshot]',tail]
        # obs_snapshot belongs to this original physical driver, not a fake view.
        assert 'proc obs_snapshot ' in contracts
        env=','.join(['PINXY_OUTPUT='+str(out),'PINXY_ACCESS_ALL=1','PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz'),
          'PINXY_CHAIN_RESERVATIONS='+str(reservations[0]),'PINXY_CHAIN_EXPORT_ACCESS='+str(DRIVER/'export_access.tcl')])
        native('route',lines,env)
        fresh=out/'fresh.tcl';fresh.write_text('read_db '+tcl(out/'routed.odb')+'\nset_routing_layers -signal metal2-metal8 -clock metal4-metal8\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
        rec['fresh_DRC_returncode']=execute(common,fresh,out/'independent.log',threads=1)
        if rec['fresh_DRC_returncode']==0:rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
        rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
        rec['pin_PG_die_unchanged']={k:sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['pins','pdn','die']}
        for kind in ['setup','hold']:
            m=re.search(r'worst slack (?:max|min)\s+([-\d.]+)',(out/(kind+'.txt')).read_text());assert m;rec[kind+'_ns']=float(m[1])
        rec['literal_VIOLATED_markers_not_complete_failure_count']=(out/'checks.txt').read_text().count('(VIOLATED)')
    except Exception as error:
        rec['exception']=str(error);(out/'driver_error.txt').write_text(traceback.format_exc())
    if (out/'route.stages.tsv').exists():
        with (out/'route.stages.tsv').open() as h:rec['route_stage_status']={r['stage']:r['status'] for r in csv.DictReader(h,delimiter='\t')}
    rec['all_sources_unchanged']=all(sha(Path(k))==v for k,v in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={q.name:{'bytes':q.stat().st_size,'sha256':sha(q)} for q in out.iterdir() if q.is_file() and q.name!='execution.json'}
    save()
    passed=('exception' not in rec and rec.get('fresh_DRC_count')==0 and rec.get('setup_ns',-1)>=0
      and rec.get('hold_ns',-1)>=0 and rec.get('literal_VIOLATED_markers_not_complete_failure_count')==0
      and rec['all_sources_unchanged'] and rec.get('whole_signal_geometry',{}).get('pass')
      and all(rec.get('pin_PG_die_unchanged',{}).get(k) for k in ['pins','pdn','die'])
      and all(rec.get('route_stage_status',{}).get(k)=='EXECUTED' for k in ['global_route','detailed_route','preserve_contracts','VDD','VSS','whole_signal_geometry','rcx','sta']))
    return 0 if passed else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
