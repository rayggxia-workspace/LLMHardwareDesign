"""Actual source-bound routed GEMM/MXU views; never full qualification."""
from pathlib import Path
import csv,datetime,json,os,re,shutil,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from lef_view_contract import parse,verify

DRIVER=Path(__file__).resolve().parent


def run(revision,kind='gemm658'):
    assert kind in ['gemm658','mxu_pin_escape','system_stacked_vias','llsys_via_tips','mxu_via_tip','llsys_parent_tip','llsys_owned_restored'];restored=kind=='llsys_owned_restored';mxu=kind=='mxu_pin_escape';system=kind=='system_stacked_vias';noap=kind=='llsys_parent_tip';llsys=kind in ['llsys_via_tips','llsys_parent_tip','llsys_owned_restored'];mxutip=kind=='mxu_via_tip';tip=llsys or mxutip
    case,count,relative,family={'gemm658':('gemm',3753,'antenna_incremental_eco/r01/gemm-C','diode_views'),
      'mxu_pin_escape':('mxu',2172,'pin_escape_route/r02/mxu-C','pin_escape_views'),
      'system_stacked_vias':('opentpu_aux',2229,'system_stacked_via_route/r01/opentpu_aux-C','system_stacked_via_views'),
      'llsys_via_tips':('llaccel_aux',13507,'llsys_actual_via_tips/r02','llsys_actual_tip_views'),
      'mxu_via_tip':('mxu',2172,'mxu_actual_via_tip/r01','mxu_actual_tip_views'),
      'llsys_parent_tip':('llaccel_aux',13507,'llsys_parent_access_tip/r01','llsys_parent_tip_views'),
      'llsys_owned_restored':('llaccel_aux',13507,'owned_cap_wire_restore/r01','llsys_owned_restored_views')}[kind]
    source=ROOT/relative;receipt=source/'execution.json';j=json.loads(receipt.read_text())
    out=ROOT/family/revision/(case+'-C');out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'ACTUAL_SOURCE_BOUND_PHYSICAL_AND_EXTRACTED_RESEARCH_VIEW_NOT_FULL_QUALIFICATION',
      'source_kind':kind,
      'full_qualification':False,'source_receipt':str(receipt),'source_receipt_SHA256':sha(receipt),
      'original_M5_M6_pins_not_raised':True,'complete_rules_and_RTL_formal':'NOT_QUALIFIED',
      'scheduler_job':os.environ['SLURM_JOB_ID'],'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip()}
    try:
        stage_key='actual_edit_and_analysis' if tip else ('detailed_edit_and_analysis' if system else 'implementation')
        assert j.get('completed_utc') and j['native_returncodes'][stage_key]==0
        if mxutip:
            recovered=ROOT/'mxu_actual_tip_fresh/r01';recovery_path=recovered/'execution.json';recovery=json.loads(recovery_path.read_text())
            assert recovery.get('completed_utc') and recovery['native_fresh_returncode']==0 and recovery['fresh_DRC_count']==0 and recovery['all_closed_sources_unchanged']
            assert recovery['source_actual_ECO_ODB_SHA256']==j['files']['routed.odb']['sha256'] and recovery['source_actual_ECO_SPEF_SHA256']==j['files']['extracted.spef']['sha256']
            assert recovery['original_allowed_signal_clock_ranges']==['metal2-metal10','metal4-metal10']
            rec['separate_original_range_fresh_receipt']=str(recovery_path);rec['separate_original_range_fresh_receipt_SHA256']=sha(recovery_path)
            rec['original_r01_DRT_0155_failure_preserved']=True
        else:
            assert j['native_returncodes']['fresh_DRC']==0 and j['fresh_DRC_count']==0
        assert j['whole_signal_geometry']['pass']
        if mxu:
            assert j['all_closed_sources_unchanged'] and j['container_libraries_unchanged']
            assert all(j['all_cells_poses_original_connections_pins_PG_die_unchanged'].values()) and j['all_original_pins_and_size_in_actual_new_LEF_identical']
        elif system:
            assert j['all_closed_sources_unchanged'] and all(j['original_cells_poses_signal_connections_pins_PG_die_unchanged'].values())
            assert j['all_other_exported_multiterminal_route_box_multisets_identical'] and j['actual_changed_multiterminal_net_wire_via_box_multisets']==['_215139_']
        elif llsys:
            assert j['all_closed_sources_unchanged'] and (restored or j['container_library_unchanged'])
            assert all(j['all_cells_signal_connections_PG_die_unchanged'].values())
            if restored:
                assert j['all_10261_current_internal_points_retained'] and j['all_other_725252_multiterminal_WIRE_VIA_multisets_exact'] and j['exactly_one_M5_WIRE_extended_all_vias_exact']
                assert j['complete_pin_contract']['only_changed_XY_pins']==[]
            elif noap:
                assert j['all_other_multiterminal_route_box_multisets_identical'] and j['unchanged_multiterminal_nets']==725252
                assert j['exact_expected_actual_WIRE_rectangles_removed_no_added_wire_or_via_material']==3
            else:
                assert j['all_other_725250_multiterminal_route_box_multisets_identical']
                assert j['exactly_eight_actual_WIRE_rectangles_removed_no_added_wire_or_via_material']
            assert restored or j['all_actual_target_via_rectangle_multisets_preserved']
            assert j['complete_pin_contract']['all_signal_pins']==count
            assert j['complete_pin_contract']['all_functions_directions_networks_layers_sizes_and_PG_preserved']
        elif mxutip:
            assert j['all_closed_sources_unchanged'] and j['container_library_unchanged']
            assert all(j['all_cells_signal_connections_PG_die_unchanged'].values())
            assert j['all_other_191437_multiterminal_route_box_multisets_identical'] and j['exactly_four_actual_M6_WIRE_rectangles_removed_all_vias_unchanged']
            assert j['complete_pin_contract']['all_signal_pins']==count and j['complete_pin_contract']['only_changed_XY_pins']==['act_data[12]']
        else:
            assert j['actual_total_real_diodes']==658 and j['all_original_instances_and_signal_graph_preserved_with_only_22_real_diode_loads']
            assert j['all_prior_functional_and_636_diode_poses_and_terminals_unchanged'] and all(j['pin_PG_die_unchanged'].values()) and j['all_sources_unchanged']
        required=[('one_actual_wire_restore' if restored else ('actual_one_net_pin_and_route_edit' if mxutip or noap else ('actual_three_net_pin_and_route_edit' if llsys else ('native_one_net_detailed_routing' if system else 'detailed_route')))),'VDD','VSS','whole_signal_geometry','rcx','sta']+([] if mxu or system or tip else ['preserve_original_views'])
        assert all(j['native_stage_status'].get(s)=='EXECUTED' for s in required)
        original=ROOT/('eco_views/'+('r03' if system else 'r02')+'/'+case+'-C')
        if not tip:
            old=json.loads((original/'execution.json').read_text())
            assert sha(original/'abstract.lef')==old['files']['abstract.lef']['sha256']
            assert sha(original/'pins.tsv')==old['files']['pins.tsv']['sha256']
        trial=ROOT/(('trials/llsys-pg-r03/' if llsys else 'trials/access-r03/')+case+'-C/execution.json');baseline=json.loads(trial.read_text());sdc=Path(baseline['source_sdc'])
        assert sha(sdc)==baseline['input_sha256'][str(sdc)]
        odb=source/'routed.odb';spef=source/'extracted.spef'
        for p in [odb,spef]+([] if mxutip else [source/'independent.drc']):assert sha(p)==j['files'][p.name]['sha256']
        originals=([source/'after.pins.tsv'] if restored else [source/'after.pins.tsv',source/('all_'+str(count)+'_actual_pin_correspondence.csv')]) if tip else [original/'execution.json',original/'abstract.lef',original/'pins.tsv']
        for p in originals:
            if tip:assert sha(p)==j['files'][p.name]['sha256']
        inputs={str(p):sha(p) for p in [receipt,odb,spef,trial,sdc]+originals}
        if mxutip:
            fresh=recovered/'independent.drc';assert sha(fresh)==recovery['files'][fresh.name]['sha256']
            inputs.update({str(p):sha(p) for p in [recovery_path,fresh]})
        rec.update({'source_SHA':inputs,'source_geometry_sha256':sha(odb),'source_SPEF_sha256':sha(spef),
          'source_native_DRC':0,'source_setup_ns':j['setup_ns'],'source_hold_ns':j['hold_ns'],
          'source_literal_violated_markers':j.get('literal_VIOLATED_markers_not_complete_failure_count')})
        if tip:
            rec['this_route_variant_new_cells_or_sizing']=0
            rec['pin_preservation_reference']='Current actual routed source after its explicitly recorded XY ECO; not the older A/B/C candidate or pre-ECO coordinates.'
            rec['inherited_costed_source']='Original MXU one sizing retained; one actual M6 via-tip XY edit adds no cells or sizing.' if mxutip else 'Complete original internal PG-only C; three actual via-tip XY edits, no added cells or resizing; negative original-source STA retained.'
            if restored:rec['inherited_costed_source']='All10261 actual internal points retained; exactly one M5 wire extended, no pin/cell/sizing/via changes; source negative setup/min kept. Geometry export patch coverage is audited separately.'
            if noap:rec['inherited_costed_source']='Complete original internal C plus three prior actual via-tip repairs retained; one further bit_1025 M5 correction adds no cell or sizing. Negative STA remains.'
            rec['source_complete_pin_contract']=j['complete_pin_contract']
        elif not (mxu or system):rec['separate_additional_diode_cost']=j['separate_additional_diode_cost']
        else:
            rec['this_route_variant_new_cells_or_sizing']=0
            rec['inherited_costed_source']='All prior SYSTEM sizing/buffering/placement costs inherited; this route variant adds none; not zero total ECO cost or pure XY benefit.' if system else 'Original MXU costed/r04 one sizing is retained; not zero total ECO cost or pure XY benefit.'
        shutil.copyfile(str(odb),str(out/'clean.odb'));assert sha(out/'clean.odb')==sha(odb)
        common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
          '--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
          '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
          '--home',str(ROOT/'home'),'--pwd',str(out)]
        for p in baseline['libs']:
            if Path(p).is_file():common+=['--bind',p+':'+p+':ro']
        lines=['read_liberty '+tcl(p) for p in baseline['libs']]
        lines+=['read_db '+tcl(out/'clean.odb'),'write_abstract_lef '+tcl(out/'abstract.lef'),
          'write_abstract_lef -bloat_factor 0 '+tcl(out/'detailed.lef'),'write_def '+tcl(out/'clean.def'),'write_verilog '+tcl(out/'clean.v'),
          'set b [ord::get_db_block];set f [open '+tcl(out/'pins.tsv')+' w];puts $f "pin\\tdirection\\tuse\\tnet\\tlayer\\tx0\\ty0\\tx1\\ty1";foreach p [$b getBTerms] {foreach bp [$p getBPins] {foreach r [$bp getBoxes] {puts $f [join [list [$p getName] [$p getIoType] [$p getSigType] [[$p getNet] getName] [[$r getTechLayer] getName] [$r xMin] [$r yMin] [$r xMax] [$r yMax]] "\\t"]}}};close $f',
          'read_sdc '+tcl(sdc),'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl','read_spef '+tcl(spef),
          'report_worst_slack -max -digits 6 > '+tcl(out/'setup.txt'),'report_worst_slack -min -digits 6 > '+tcl(out/'hold.txt'),
          'report_parasitic_annotation -report_unannotated > '+tcl(out/'parasitic_coverage.txt'),
          'check_setup -verbose > '+tcl(out/'constraint_coverage.txt'),'write_timing_model '+tcl(out/'timing.lib')]
        if mxu or mxutip:
            lines+=['set ::env(PINXY_ACCESS_ALL) 0','set ::env(PINXY_ACCESS_NET_NAMES) {act_data[12]}',
              'set ::env(PINXY_ACCESS_OUT) '+tcl(out/'target_pin_access.tsv.gz'),'source '+tcl(DRIVER/'export_access.tcl')]
        if restored:
            lines+=['set ::env(PINXY_ACCESS_ALL) 0','set ::env(PINXY_ACCESS_NET_NAMES) {bit_433}',
              'set ::env(PINXY_ACCESS_OUT) '+tcl(out/'actual_restored_bit433.tsv.gz'),'source '+tcl(DRIVER/'export_access.tcl'),
              'set ::env(PINXY_PATCH_NET_NAMES) {bit_433}','set ::env(PINXY_PATCH_OUT) '+tcl(out/'actual_restored_bit433_patches.tsv'),
              'set ::env(PINXY_PATCH_COUNTS) '+tcl(out/'actual_restored_bit433_patch_counts.tsv'),'source '+tcl(DRIVER/'export_patch_rects.tcl')]
        if system:
            lines+=['set ::env(PINXY_ACCESS_ALL) 0','set ::env(PINXY_ACCESS_NET_NAMES) {_215139_}',
              'set ::env(PINXY_ACCESS_OUT) '+tcl(out/'after_actual_target.tsv.gz'),'source '+tcl(DRIVER/'export_access.tcl'),
              'report_check_types -min_pulse_width -min_period -max_skew -clock_gating_setup -clock_gating_hold -min_slew -min_capacitance -min_fanout -max_count 1000000 -digits 6 > '+tcl(out/'current_source_extended_checks_all.txt')]
        script=out/'export.tcl';script.write_text('\n'.join(lines)+'\n')
        rec['native_export_returncode']=execute(common,script,out/'export.log')
        assert rec['native_export_returncode']==0
        if system:
            ep=out/'current_source_extended_checks_all.txt'
            rec['current_exact_source_extended_STA']={'native_command_executed':True,'literal_VIOLATED_rows_not_full_rule_coverage':ep.read_text().count('(VIOLATED)'),
              'actual_report_SHA256':sha(ep),'applicability':'Only defined constraints under original source Lib/SDC; empty/undefined checks are not passed rules. Original negative setup/hold and library minimum_period coverage remain.'}
            before=ROOT/'system_patch_route/r02/opentpu_aux-C';bp=before/'execution.json';previous=json.loads(bp.read_text())
            assert previous.get('completed_utc') and previous['fresh_DRC_count']==2
            before_odb=before/'routed.odb';assert sha(before_odb)==previous['files']['routed.odb']['sha256']
            inputs.update({str(p):sha(p) for p in [bp,before_odb]})
            rec['before_actual_geometry_sha256']=sha(before_odb)
            script=out/'before_target.tcl';script.write_text('read_db '+tcl(before_odb)+'\nset ::env(PINXY_ACCESS_ALL) 0\nset ::env(PINXY_ACCESS_NET_NAMES) {_215139_}\nset ::env(PINXY_ACCESS_OUT) '+tcl(out/'before_actual_target.tsv.gz')+'\nsource '+tcl(DRIVER/'export_access.tcl')+'\n')
            rec['before_target_actual_export_returncode']=execute(common,script,out/'before_target.log',threads=1)
            assert rec['before_target_actual_export_returncode']==0
        rec['detailed_OBS_view_contract']=verify(out/'abstract.lef',out/'detailed.lef')
        if tip:
            from collections import Counter
            def pin_tokens(s):
                r=s.split();assert len(r)==9
                for i in [0,3]:
                    if r[i].startswith('{') and r[i].endswith('}'):r[i]=r[i][1:-1]
                return tuple(r)
            actual=[pin_tokens(s) for s in (out/'pins.tsv').read_text().splitlines()[1:]]
            expected=[pin_tokens(s) for s in (source/'after.pins.tsv').read_text().splitlines()]
            assert Counter(actual)==Counter(expected),'Every source signal/clock/PG pin must match the real edited ODB'
            rec['all_'+str(count)+'_current_pins_and_PG_match_actual_after_edit']=True
            rec['historical_parent_target_layers']='PARTIAL_OR_UNKNOWN_UNCHANGED; new controlled parent still requires actual access validation'
        else:
            assert parse(original/'abstract.lef')[:2]==parse(out/'abstract.lef')[:2]
            assert (original/'pins.tsv').read_bytes()==(out/'pins.tsv').read_bytes()
        rec['all_original_signal_and_PG_pins_and_size_exactly_preserved']=True
        rec['SPEF_replay_matches_source']=all((source/(k+'.txt')).read_text()==(out/(k+'.txt')).read_text() for k in ['setup','hold'])
        assert rec['SPEF_replay_matches_source']
        check=out/'read_model.tcl';check.write_text('read_liberty '+tcl(out/'timing.lib')+'\nset f [open '+tcl(out/'model_pins.tsv')+' w];puts $f "pin\\tdirection";foreach p [get_lib_pins -of_objects [get_lib_cells *]] {puts $f "[get_full_name $p]\\t[get_property $p direction]"};close $f\n')
        rec['fresh_model_read_returncode']=execute(common,check,out/'read_model.log',threads=1)
        assert rec['fresh_model_read_returncode']==0
        with (out/'pins.tsv').open() as f:physical=list(csv.DictReader(f,delimiter='\t'))
        expected={p['pin'].replace('\\',''):p['direction'].lower() for p in physical if p['use'] not in ['POWER','GROUND']}
        pg={p['pin'].replace('\\','') for p in physical if p['use'] in ['POWER','GROUND']}
        with (out/'model_pins.tsv').open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
        pins={p['pin'].split('/')[-1].replace('\\',''):p['direction'].lower() for p in rows};assert len(pins)==len(rows)
        for extra in set(pins)-set(expected)-pg:
            members=[p for p in expected if re.fullmatch(re.escape(extra)+r'\[\d+\]',p)]
            assert len(members)>1 and all(expected[p]==pins[extra] for p in members)
        assert {p:d for p,d in pins.items() if p in expected}==expected and len(expected)==count
        rec['matching_all_signal_model_pins']=count
        rec['minimum_period_present']='minimum_period' in (out/'timing.lib').read_text()
        rec['all_sources_and_pre_RCX_geometry_unchanged']=all(sha(Path(p))==v for p,v in inputs.items()) and sha(out/'clean.odb')==sha(odb)
        assert rec['all_sources_and_pre_RCX_geometry_unchanged']
        if mxu or mxutip:
            target=[p for p in physical if p['pin'].replace('\\','')=='act_data[12]'];assert len(target)==1 and target[0]['layer']=='metal6'
            box=[int(target[0][k])/2000 for k in ['x0','y0','x1','y1']];window=[box[0]-1.5,box[1]-1.5,box[2]+1.5,box[3]+1.5]
            local=[];polygons=[];inside=False;layer=None
            with (out/'detailed.lef').open() as f:
                for line in f:
                    line=line.strip()
                    if line=='OBS':inside=True
                    elif inside and line.startswith('LAYER '):layer=line.split()[1]
                    elif inside and layer=='metal6' and line.startswith('RECT '):
                        r=list(map(float,line.split()[1:5]))
                        if r[0]<=window[2] and r[2]>=window[0] and r[1]<=window[3] and r[3]>=window[1]:local.append(r)
                    elif inside and layer=='metal6' and line.startswith('POLYGON '):polygons.append(line)
                    elif inside and line=='END':inside=False
            context={'scope':'Actual local detailed LEF M6 OBS; no free-space or DRC inference','original_pin_box_um':box,'window_um':window,
              'actual_M6_OBS_rectangles_um':local,'M6_polygon_lines_not_silently_treated_as_empty':polygons,
              'new_parent_access':'NOT_EXECUTED','DBU_per_um':2000,'full_qualification':False}
            (out/'actual_M6_OBS_context.json').write_text(json.dumps(context,indent=2)+'\n');rec['actual_M6_OBS_context']=context
        rec['status']='ACTUAL_SOURCE_VIEW_EXPORTED_NOT_QUALIFIED_COMMON_BASE_OR_FULL_SYSTEM'
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return 0 if 'actual_failure' not in rec and rec.get('matching_all_signal_model_pins')==count else 1


if __name__=='__main__':sys.exit(run(*sys.argv[1:3]))
