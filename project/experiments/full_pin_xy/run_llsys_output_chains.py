"""Move existing private buffers on source-proven failing LL output paths.

Native geometry-only selection/legalization processes are separate from STA.
No new functional cell, master sizing, signal net split, pin/PG/OBS or original
SDC edit. Final whole-block route/RC/STA/fresh checks, not heuristic estimates,
decide the outcome. Other setup, hold and removal failures remain independent.
"""
from pathlib import Path
import csv,datetime,json,os,re,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,BIN,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from buffer_graph_contract import identity_buffer
from cell_semantics import groups
from check_access import check

DRIVER=Path(__file__).resolve().parent


def run(revision):
    assert int(os.environ['SLURM_CPUS_PER_TASK'])>=4
    source=ROOT/'llsys_parent_access_tip/r01';rp=source/'execution.json';prior=json.loads(rp.read_text())
    assert prior.get('completed_utc') and prior['fresh_DRC_count']==0 and prior['whole_signal_geometry']['pass']
    assert prior['all_closed_sources_unchanged'] and all(prior['all_cells_signal_connections_PG_die_unchanged'].values())
    assert prior['complete_pin_contract']['all_signal_pins']==13507
    odb=source/'routed.odb';spef=source/'extracted.spef'
    for p in [odb,spef,source/'fresh.tcl']:
        assert sha(p)==prior['files'][p.name]['sha256']
    assert 'set_routing_layers -signal metal2-metal8 -clock metal4-metal8' in (source/'fresh.tcl').read_text()
    audit=ROOT/'actual_path_audit/r03/llaccel_aux';ap=audit/'execution.json';a=json.loads(ap.read_text())
    assert a['native_returncode']==0 and a['all_sources_unchanged'] and all(a['source_worst_slacks_exactly_replayed'].values())
    for p in [odb,spef]:assert a['source_SHA'][str(p)]==sha(p)
    paths=audit/'setup_paths.json';assert sha(paths)==a['files'][paths.name]['sha256']
    observed=json.loads(paths.read_text())['checks']
    targets=sorted({r['endpoint'] for r in observed if r['path_type']=='max' and r['path_group']=='clk' and r['slack']<0 and re.fullmatch(r'bit_\d+',r['endpoint'])})
    assert targets and 'bit_2941' in targets
    trial=ROOT/'trials/llsys-pg-r03/llaccel_aux-C/execution.json';old=json.loads(trial.read_text());sdc=Path(old['source_sdc'])
    assert sha(sdc)==old['input_sha256'][str(sdc)]
    # This actual LL source did not use the openTPU temporary reservations.
    assert not any(p.endswith('/access_reservations.tcl') for p in old['input_sha256'])
    out=ROOT/'llsys_output_chain'/revision;out.mkdir(parents=True,exist_ok=False)
    inputs={str(p):sha(p) for p in [rp,odb,spef,source/'fresh.tcl',ap,paths,trial,sdc]}
    rec={'scope':'SOURCE_DIRECTED_EXISTING_LL_OUTPUT_BUFFER_PLACEMENT_AND_REAL_ROUTE_NOT_PURE_PIN_XY',
      'source_SHA':inputs,'source_actual_ODB_SHA256':sha(odb),'source_max_min_slack_ns':[prior['setup_ns'],prior['hold_ns']],
      'minimum_slack_includes_removal_not_only_hold':True,'selected_actual_negative_output_ports':targets,
      'selection_coverage':'Only reported failing output endpoints; all other outputs retained and all 13507 original signals still validated',
      'requested_new_functional_cells':0,'requested_master_sizing_changes':0,'requested_functional_net_splits':0,
      'all_original_internal_pin_XY_layers_sizes_and_PG_to_be_preserved':True,
      'allowed_layers':'Original signal M2-M8; clock M4-M8','temporary_reservations':'None in original LL source; original actual OBS/PG retained',
      'placement_policy':'Reuse proven identity-buffer selection and driver-bbox/actual-pin interpolation; bbox is a placement proxy, not a fabricated logical endpoint',
      'separate_processes':'No Liberty/SDC/STA observers in selection or legalization; original SDC loaded for actual route/RC/STA',
      'RTL_formal_equivalence':'NOT_EXECUTED','complete_rules':'NOT_QUALIFIED','full_qualification':False,
      'native_returncodes':{},'scheduler_job':os.environ['SLURM_JOB_ID'],
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
      'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    def save():(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    save()
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
      '--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
      '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
      '--home',str(ROOT/'home'),'--pwd',str(out)]
    for path in old['libs']:
        if Path(path).is_file():common+=['--bind',path+':'+path+':ro']
    helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
    original_code=(DRIVER/'output_chain_placement.tcl').read_text()
    contracts=original_code.split('read_db $::env(PINXY_CHAIN_SOURCE)',1)[0]
    def native(label,body,env=None,threads=4):
        script=out/(label+'.tcl');h=helper.replace('$out/stages.tsv','$out/'+label+'.stages.tsv')
        script.write_text(h+'\n'+body+'\n')
        rc=execute(common,script,out/(label+'.log'),env or 'PINXY_OUTPUT='+str(out),threads=threads)
        rec['native_returncodes'][label]=rc;save()
        if rc:raise RuntimeError(label+' native failure '+str(rc))
    try:
        rec['actual_OpenROAD_binary_SHA256']=subprocess.check_output(common+[IMAGE,'sha256sum',BIN]).decode().split()[0]
        assert rec['actual_OpenROAD_binary_SHA256']==prior['actual_OpenROAD_binary_SHA256']
        lib='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
        raw=subprocess.check_output(common+[IMAGE,'cat',lib]);rec['actual_Liberty_SHA256']=__import__('hashlib').sha256(raw).hexdigest()
        assert rec['actual_Liberty_SHA256']==prior['original_container_library_SHA256']
        text=raw.decode();allowed={}
        for name,body in groups(text,'cell'):
            if re.fullmatch(r'(?:CLKBUF|BUF)_X\d+',name):
                ip,op,_=identity_buffer(text,name);allowed[name]=(ip,op)
        assert allowed;rec['actual_identity_buffer_models']=allowed
        models=out/'actual_buffer_models.tcl';models.write_text('set buffer_models [dict create]\n'+''.join('dict set buffer_models '+tcl(n)+' {'+ip+' '+op+'}\n' for n,(ip,op) in sorted(allowed.items())))
        selected='set target_output_ports [dict create]\n'+''.join('dict set target_output_ports '+tcl(n)+' 1\n' for n in targets)
        prefix=original_code.split('if {![stage legalization {',1)[0]
        assert prefix.count('read_sdc $::env(PINXY_CHAIN_SDC)')==1
        prefix=prefix.replace('read_sdc $::env(PINXY_CHAIN_SDC)','').replace('source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl','')
        marker='foreach port [$b getBTerms] {';assert prefix.count(marker)==1
        prefix=prefix.replace(marker,marker+'\n if {![dict exists $target_output_ports [$port getName]]} {if {[$port getIoType] eq "OUTPUT"} {puts $f [join [list [$port getName] PRESERVED_NOT_REPORTED_NEGATIVE_OUTPUT {} 0] "\\t"]};continue}',1)
        prefix+='\nset f [open '+tcl(out/'original_status.tcl')+' w];puts $f {set original_status [dict create]}\nforeach row $original_status {lassign $row i status;puts $f [list dict set original_status [$i getName] $status]}\nputs $f [list set filler_masters $filler_masters];close $f\nclose $stages\n'
        env=','.join(['PINXY_OUTPUT='+str(out),'PINXY_CHAIN_SOURCE='+str(odb),'PINXY_CHAIN_MODELS='+str(models)])
        native('selection_and_moves',selected+prefix,env)
        with (out/'proposed_existing_buffer_moves.tsv').open() as f:moves=list(csv.DictReader(f,delimiter='\t'))
        assert moves and len({r['instance'] for r in moves})==len(moves)
        assert {r['port'] for r in moves}<=set(targets)
        rec['selected_existing_buffers']=len(moves);rec['selected_output_chains']=len({r['port'] for r in moves});save()
        selection='set selected_buffers [dict create]\n'+''.join('dict set selected_buffers '+tcl(r['instance'])+' {}\n' for r in moves)
        lines=[contracts,selection,'read_db '+tcl(out/'moved_NOT_LEGALIZED_OR_ROUTED.odb'),
          'set b [ord::get_db_block]','source '+tcl(out/'original_status.tcl'),
          'if {![stage isolated_legalization_no_STA {detailed_placement -use_diamond_legalizer}]} {close $stages;exit 1}',
          'dict for {name status} $original_status {set i [$b findInst $name];if {$i eq "NULL"} {error "Original instance missing"};$i setPlacementStatus $status}',
          'if {![stage check_and_restore_fillers {check_placement -verbose;if {[llength $filler_masters]} {filler_placement -prefix PINXY_LL_CHAIN_FILL_ $filler_masters};global_connect;check_placement -verbose}]} {close $stages;exit 1}',
          'connection_contract '+tcl(out/'placed.connections.tsv'),'nonselected_pose_contract '+tcl(out/'placed.nonselected.tsv'),
          'write_db '+tcl(out/'placed_NOT_ROUTED.odb'),'close $stages']
        native('legalization','\n'.join(lines))
        rec['isolated_geometry_contracts']={k:sha(out/('before.'+k+'.tsv'))==sha(out/('placed.'+k+'.tsv')) for k in ['connections','nonselected']}
        assert all(rec['isolated_geometry_contracts'].values());save()
        reservations=out/'original_no_temporary_reservations.tcl';reservations.write_text('set access_reservations {}\n')
        tail='set temporary_obs {};'+original_code.split('set temporary_obs {};',1)[1]
        lines=[contracts,selection]+['read_liberty '+tcl(p) for p in old['libs']]+['read_db '+tcl(out/'placed_NOT_ROUTED.odb'),
          'read_sdc '+tcl(sdc),'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl',
          'set b [ord::get_db_block];set u [$b getDbUnitsPerMicron];set original_obs [obs_snapshot]',tail]
        env=','.join(['PINXY_OUTPUT='+str(out),'PINXY_ACCESS_ALL=1','PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz'),
          'PINXY_CHAIN_RESERVATIONS='+str(reservations),'PINXY_CHAIN_EXPORT_ACCESS='+str(DRIVER/'export_access.tcl')])
        native('route_RC_STA','\n'.join(lines),env)
        native('fresh_DRC','read_db '+tcl(out/'routed.odb')+'\nset_routing_layers -signal metal2-metal8 -clock metal4-metal8\ndrt::check_drc -output_file '+tcl(out/'independent.drc'),threads=1)
        rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
        rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
        rec['pin_PG_die_unchanged']={k:sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['pins','pdn','die']}
        rec['same_functional_cells_masters_connections_and_nonselected_poses']={k:sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['connections','nonselected']}
        for kind in ['setup','hold']:
            rec[kind+'_ns']=float(re.search(r'worst slack (?:max|min)\s+([-\d.]+)',(out/(kind+'.txt')).read_text())[1])
        rec['literal_VIOLATED_markers_not_complete_failure_count']=(out/'checks.txt').read_text().count('(VIOLATED)')
        rec['actual_native_binary_and_Liberty_unchanged']=(subprocess.check_output(common+[IMAGE,'sha256sum',BIN]).decode().split()[0]==rec['actual_OpenROAD_binary_SHA256'] and subprocess.check_output(common+[IMAGE,'sha256sum',lib]).decode().split()[0]==rec['actual_Liberty_SHA256'])
    except Exception:rec['actual_failure']=traceback.format_exc();traceback.print_exc()
    if (out/'route_RC_STA.stages.tsv').exists():
        with (out/'route_RC_STA.stages.tsv').open() as f:rec['native_route_stage_status']={r['stage']:r['status'] for r in csv.DictReader(f,delimiter='\t')}
    rec['all_sources_unchanged']=all(sha(Path(p))==h for p,h in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    passed=('actual_failure' not in rec and rec.get('fresh_DRC_count')==0 and rec.get('whole_signal_geometry',{}).get('pass') and rec['all_sources_unchanged'] and rec.get('actual_native_binary_and_Liberty_unchanged')
      and all(rec.get('pin_PG_die_unchanged',{}).get(k) for k in ['pins','pdn','die'])
      and all(rec.get('same_functional_cells_masters_connections_and_nonselected_poses',{}).get(k) for k in ['connections','nonselected'])
      and rec.get('setup_ns',-1)>=0 and rec.get('hold_ns',-1)>=0 and rec.get('literal_VIOLATED_markers_not_complete_failure_count')==0
      and all(rec.get('native_route_stage_status',{}).get(k)=='EXECUTED' for k in ['global_route','detailed_route','preserve_contracts','VDD','VSS','whole_signal_geometry','rcx','sta']))
    return 0 if passed else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
