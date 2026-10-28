"""Two evidence-selected drive-size repairs after the actual diode route.

Real diode inventory, nets, pin layers/rectangles, PG, SDC and allowed layers
remain. Added implementation cost is separate from pin XY and from diode cost.
"""
from pathlib import Path
import csv,datetime,json,os,re,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from run_vector_resume import COST_PROC
from run_checkpoint_route import OBS_PROC
from cell_semantics import check_pair,groups
from verify_mapped_eco import export_graph,load
from check_access import check

DRIVER=Path(__file__).resolve().parent
REPLACEMENTS=[('_328822_','INV_X1','INV_X2',67.621605),('_332783_','XNOR2_X1','XNOR2_X2',27.449909)]


def run(revision):
    source=ROOT/'antenna_diode_eco/r01/gemm-C';p=source/'execution.json';proof=json.loads(p.read_text())
    assert proof.get('completed_utc') and proof['native_returncodes']['implementation']==0
    assert proof['fresh_DRC_count']==0 and proof['whole_signal_geometry']['pass'] and proof['all_sources_unchanged']
    assert all(proof['unchanged_geometry'].values()) and proof['separate_diode_cost']['inserted_real_ANTENNA_X1']==636
    prior=ROOT/'passive_load_equivalence/r01/gemm';pr=json.loads((prior/'execution.json').read_text())
    assert pr['relative_mapped_digital_contract_pass'] and pr['all_stable_geometry_and_source_files_unchanged']
    odb=source/'routed.odb';guide=source/'route.guide';before_graph=prior/'real_diodes.tsv.gz'
    assert sha(odb)==proof['files'][odb.name]['sha256']==pr['source_SHA'][str(odb)]
    assert sha(guide)==proof['files'][guide.name]['sha256'] and sha(before_graph)==pr['files'][before_graph.name]['sha256']
    checks=(source/'checks.txt').read_text();assert checks.count('(VIOLATED)')==2
    assert all(name+'/ZN' in checks for name,old,new,cap in REPLACEMENTS)
    original=json.loads((ROOT/'trials/access-r03/gemm-C/execution.json').read_text());sdc=Path(original['source_sdc'])
    reservations=[Path(k) for k in original['input_sha256'] if k.endswith('/access_reservations.tcl')];assert len(reservations)==1
    for q in [sdc,reservations[0]]:assert sha(q)==original['input_sha256'][str(q)]
    out=ROOT/'diode_cap_eco'/revision/'gemm-C';out.mkdir(parents=True,exist_ok=False)
    inputs={str(q):sha(q) for q in [p,odb,guide,sdc,reservations[0],source/'checks.txt',prior/'execution.json',before_graph]}
    rec={'scope':'TWO_REAL_DIODE_ROUTE_CAP_REPAIRS_SEPARATE_COST_NOT_PURE_XY',
      'source_SHA':inputs,'full_qualification':False,'original_clocks_loads_and_allowed_layers_preserved':True,
      'original_allowed_layers':'signal M2-M10; clock M4-M10','new_buffers_or_diodes_requested':0,
      'incremental_GRT_not_claimed_two_net_only_DRT':True,
      'retained_real_diode_count':636,'RTL_formal_equivalence':'NOT_EXECUTED','complete_GDS_rules':'NOT_YET_EXECUTED',
      'native_returncodes':{},'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
      'scheduler_job':os.environ['SLURM_JOB_ID'],'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    def save():(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    save()
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
      '--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
      '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
      '--home',str(ROOT/'home'),'--pwd',str(out)]
    for path in original['libs']:
        if Path(path).is_file():common+=['--bind',path+':'+path+':ro']
    try:
        lib='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
        text=subprocess.check_output(common+[IMAGE,'cat',lib]).decode();libfile=out/'actual_typical.lib';libfile.write_text(text)
        semantics=[]
        cells=dict(groups(text,'cell'))
        for inst,old,new,cap in REPLACEMENTS:
            result=check_pair([libfile],old,new)
            output=dict(groups(cells[new],'pin'))['ZN'];limit=float(re.search(r'\bmax_capacitance\s*:\s*([\d.eE+-]+)',output).group(1))
            assert limit>cap,('Actual stronger master cannot drive measured cap',inst,new,limit,cap)
            semantics.append({'instance':inst,'old_master':old,'new_master':new,'measured_source_cap_ff':cap,
              'actual_new_master_max_cap_ff':limit,'actual_liberty_logic_state_contract':result})
        rec['actual_sizing_contracts']=semantics;save()
        helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
        lines=[helper,COST_PROC,OBS_PROC]+['read_liberty '+tcl(path) for path in original['libs']]
        lines+=['read_db '+tcl(odb),'read_sdc '+tcl(sdc),'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl',
          'set b [ord::get_db_block];set u [$b getDbUnitsPerMicron];set original_obs {};foreach ob [$b getObstructions] {lappend original_obs [obs_contract $ob]};set temporary_obs {}',
          'fingerprint '+tcl(out/'before'),'cell_cost '+tcl(out/'before.cell_cost.tsv'),
          'set access_reservations {};source '+tcl(reservations[0]),
          'foreach row $access_reservations {lassign $row ly x0 y0 x1 y1;set coords {};foreach v [list $x0 $y0 $x1 $y1] {lappend coords [expr {round($v*$u)}]};lappend temporary_obs [odb::dbObstruction_create $b [[ord::get_db_tech] findLayer $ly] {*}$coords]}',
          'set_routing_layers -signal metal2-metal10 -clock metal4-metal10','read_guides '+tcl(guide),
          'if {![stage begin_incremental_GRT {global_route -start_incremental}]} {close $stages;exit 1}',
          'set filler_masters {};foreach i [$b getInsts] {if {[[$i getMaster] getType] eq "CORE_SPACER"} {lappend filler_masters [[$i getMaster] getName]}};set filler_masters [lsort -unique $filler_masters]',
          'if {![stage exact_two_swaps {remove_fillers']
        for inst,old,new,cap in REPLACEMENTS:
            lines.append('set i [$b findInst '+tcl(inst)+'];if {$i eq "NULL" || [[$i getMaster] getName] ne '+tcl(old)+'} {error "Actual old master differs"};if {![$i swapMaster [[ord::get_db] findMaster '+tcl(new)+']]} {error "Actual master swap failed"}')
        lines+=['}]} {close $stages;exit 1}','write_db '+tcl(out/'resized_NOT_LEGALIZED_OR_ROUTED.odb'),
          'if {![stage placement {detailed_placement -incremental;check_placement -verbose;if {[llength $filler_masters]} {filler_placement -prefix PINXY_DIODE_CAP_FILL_ $filler_masters};global_connect;check_placement -verbose}]} {close $stages;exit 1}',
          'write_db '+tcl(out/'resized_placed_NOT_ROUTED.odb'),
          'if {![stage global_route {global_route -end_incremental -guide_file '+tcl(out/'route.guide')+' -congestion_report_file '+tcl(out/'congestion.rpt')+'}]} {close $stages;exit 1}',
          'if {![stage detailed_route {detailed_route -output_drc '+tcl(out/'route.drc')+' -verbose 1}]} {close $stages;exit 1}',
          'foreach ob $temporary_obs {odb::dbObstruction_destroy $ob};set obs_after {};foreach ob [$b getObstructions] {lappend obs_after [obs_contract $ob]};if {[lsort $obs_after] ne [lsort $original_obs]} {error "Original OBS changed"}',
          'fingerprint '+tcl(out/'after'),'cell_cost '+tcl(out/'after.cell_cost.tsv'),'write_db '+tcl(out/'routed.odb'),'write_def '+tcl(out/'routed.def'),'write_verilog '+tcl(out/'mapped.v'),
          'report_wire_length -detailed_route -summary -file '+tcl(out/'wire_length.csv'),
          'stage VDD {check_power_grid -net VDD -error_file '+tcl(out/'VDD.rpt')+'}',
          'stage VSS {check_power_grid -net VSS -error_file '+tcl(out/'VSS.rpt')+'}',
          'stage whole_signal_geometry {source '+tcl(DRIVER/'export_access.tcl')+'}',
          'stage rcx {define_process_corner -ext_model_index 0 X;set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules;extract_parasitics;write_spef '+tcl(out/'extracted.spef')+';read_spef '+tcl(out/'extracted.spef')+'}',
          'stage sta {report_worst_slack -max -digits 6 > '+tcl(out/'setup.txt')+';report_worst_slack -min -digits 6 > '+tcl(out/'hold.txt')+';report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > '+tcl(out/'checks.txt')+';check_setup -verbose > '+tcl(out/'constraint_coverage.txt')+';report_parasitic_annotation -report_unannotated > '+tcl(out/'parasitic_coverage.txt')+'}','close $stages']
        script=out/'run.tcl';script.write_text('\n'.join(lines)+'\n')
        env='PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz')
        rec['native_returncodes']['implementation']=execute(common,script,out/'native.log',env);save()
        if (out/'routed.odb').exists():
            fresh=out/'fresh.tcl';fresh.write_text('read_db '+tcl(out/'routed.odb')+'\nset_routing_layers -signal metal2-metal10 -clock metal4-metal10\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
            rec['native_returncodes']['fresh_DRC']=execute(common,fresh,out/'independent.log',threads=1)
            if rec['native_returncodes']['fresh_DRC']==0:rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
            rec['native_returncodes']['relative_graph_export']=export_graph(common,out/'routed.odb',out,'resized')
            assert rec['native_returncodes']['relative_graph_export']==0
            a,at,ap=load(before_graph);b,bt,bp=load(out/'resized.tsv.gz');assert set(a)==set(b) and at==bt and ap==bp
            changed={n:(a[n][0],b[n][0]) for n in a if a[n]!=b[n]}
            assert changed=={inst:(old,new) for inst,old,new,cap in REPLACEMENTS}
            assert sum(m[0]=='ANTENNA_X1' for m in b.values())==636
            rec['all_original_signal_terminal_and_port_graph_equal_with_exact_two_proven_sizes']=True
        if (out/'whole_access.tsv.gz').exists():rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
        rec['pin_PG_die_unchanged']={k:(out/('after.'+k+'.tsv')).exists() and sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['pins','pdn','die']}
        costs=[]
        for label in ['before','after']:
            q=out/(label+'.cell_cost.tsv')
            if q.exists():
                with q.open() as f:costs.append({r['instance']:r for r in csv.DictReader(f,delimiter='\t') if r['type']!='CORE_SPACER'})
        if len(costs)==2:
            a,b=costs;assert set(a)==set(b)
            rec['separate_two_size_ECO_cost']={'changed_masters':sum(a[n]['master']!=b[n]['master'] for n in a),
              'moved_existing_instances':sum((a[n]['x_dbu'],a[n]['y_dbu'])!=(b[n]['x_dbu'],b[n]['y_dbu']) for n in a),
              'added_functional_instances':0,'standard_cell_master_bbox_area_delta_um2':sum(float(b[n]['area_um2'])-float(a[n]['area_um2']) for n in a),
              'not_block_area_saving_or_pure_pin_XY':True}
        for kind in ['setup','hold']:
            q=out/(kind+'.txt')
            if q.exists():
                m=re.search(r'worst slack (?:min|max)\s+([-\d.]+)',q.read_text());assert m;rec[kind+'_ns']=float(m[1])
        if (out/'checks.txt').exists():rec['literal_VIOLATED_markers_not_complete_failure_count']=(out/'checks.txt').read_text().count('(VIOLATED)')
    except Exception:
        rec['actual_failure']=traceback.format_exc()
    if (out/'stages.tsv').exists():
        with (out/'stages.tsv').open() as f:rec['native_stage_status']={r['stage']:r['status'] for r in csv.DictReader(f,delimiter='\t')}
    rec['all_sources_unchanged']=all(sha(Path(k))==v for k,v in inputs.items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    passed=('actual_failure' not in rec and rec.get('fresh_DRC_count')==0 and rec.get('setup_ns',-1)>=0 and rec.get('hold_ns',-1)>=0
      and rec.get('literal_VIOLATED_markers_not_complete_failure_count')==0 and rec['all_sources_unchanged']
      and rec.get('whole_signal_geometry',{}).get('pass') and rec.get('all_original_signal_terminal_and_port_graph_equal_with_exact_two_proven_sizes')
      and all(rec.get('pin_PG_die_unchanged',{}).get(k) for k in ['pins','pdn','die'])
      and all(rec.get('native_stage_status',{}).get(k)=='EXECUTED' for k in ['exact_two_swaps','placement','global_route','detailed_route','VDD','VSS','whole_signal_geometry','rcx','sta']))
    return 0 if passed else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
