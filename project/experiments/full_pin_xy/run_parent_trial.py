"""Actual NEW parent A/replay/Aopt/B/C access, fixed parent PG and resources.

Physical source views must already have independent clean native checks. Stubs
are explicitly not timing models; no parent STA/electrical pass is claimed.
"""
from pathlib import Path
from collections import defaultdict
import csv,datetime,json,os,re,subprocess,sys,traceback
from run_exports import ROOT,CFG,IMAGE,BIN,sha
from check_access import check
from lef_view_contract import verify as verify_lef_view
DRIVER=Path(__file__).resolve().parent
BASE={'act':'r02','gemm':'r01','mxu':'r03','vector':'r04','opentpu_aux':'r03','llaccel_aux':'r03'}

def tcl(value):
    assert not any(c in str(value) for c in '{}\n\r'),value
    return '{'+str(value)+'}'

def child_source(case,plan):
    if plan in ['A','A_replay']:rev,p=BASE[case],'A'
    elif case=='act':rev,p={'A_child_replay':('fullC-r01','A_replay'),'Aopt':('full-controls-r04','Aopt'),'B':('fullBcohort-r01','B'),'C':('fullC-r02','C')}[plan]
    else:rev,p=('full-other-r01','C') if plan=='C' else ('full-controls-r04','A_replay' if plan=='A_child_replay' else plan)
    directory=ROOT/'finalized'/rev/(case+'-'+p);j=json.loads((directory/'execution.json').read_text())
    assert j['independent_DRC_count']==0 and j['whole_access']['pass'] and j['clean_byte_identical_to_pre_RCX_source'],('Unverified child geometry',case,plan)
    lef=directory/'abstract.lef';assert sha(lef)==j['files']['abstract.lef']['sha256']
    return lef,j,directory/'execution.json'

def alias_view(source,dest,original,alias):
    text=source.read_text();text,n=re.subn(r'(?m)^MACRO '+re.escape(original)+r'\s*$', 'MACRO '+alias,text);assert n==1
    text,n=re.subn(r'(?m)^END '+re.escape(original)+r'\s*$', 'END '+alias,text);assert n==1
    dest.write_text(text)

def validate_graph(path,contract,expected):
    with path.open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
    key=lambda r:(r['kind'],r.get('instance',''),r['pin'])
    physical={key(r):r for r in rows};assert len(physical)==len(rows)==len(expected)
    logical={key(r):r for r in expected};assert set(logical)==set(physical),'Parent terminal set changed'
    top={p['pin']:p for p in contract['external_pins']};bit_nets=defaultdict(set);net_bits=defaultdict(set)
    for k,want in logical.items():
        got=physical[k];assert got['direction'].lower()==want['direction'],(k,'direction')
        layer=want.get('original_leaf_pin_layer',top[want['pin']]['layer'] if want['kind']=='BTERM' else None)
        assert got['layer']==layer,(k,'physical target layer',got['layer'],layer)
        bit_nets[want['parent_bit']].add(got['net']);net_bits[got['net']].add(want['parent_bit'])
    assert all(len(v)==1 for v in bit_nets.values()) and all(len(v)==1 for v in net_bits.values()),'Logical bits merged or split'
    return {'exact_terminal_set_direction_layer_and_bit_graph':True,'endpoints':len(rows),'parent_bits':len(bit_nets),'independent_constant_nets_preserved':True}

def one(inputs,rev,plan):
    contract=json.loads((inputs/'contract.json').read_text());focus=contract['focus'];design=contract['design']
    out=ROOT/'parents'/rev/(design+'-'+focus+'-'+plan);out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'NEW_CONTROLLED_PARENT_NOT_HISTORICAL','case':focus,'design':design,'plan':plan,'parent_STA':'NOT_EXECUTED_UNCHARACTERIZED_PORT_STUBS',
      'historical_handoff':'STILL_UNKNOWN','scheduler_job':os.environ['SLURM_JOB_ID'],'allocated_cpus':os.environ['SLURM_CPUS_PER_TASK'],
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'input_contract_sha256':sha(inputs/'contract.json'),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    common=['singularity','exec','--cleanenv','--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro','--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro','--home',str(ROOT/'home'),'--pwd',str(out)]
    views={};commands=[]
    if plan=='A':
        commands += ['read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef','read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef']
        selected=list(contract['physical_instances'])
    else:
        baseline=ROOT/'parents'/rev/(design+'-'+focus+'-A');b=json.loads((baseline/'execution.json').read_text())
        assert b.get('independent_DRC_count')==0 and b.get('whole_signal_geometry',{}).get('pass'),'New baseline has not passed physical access gates'
        assert b.get('PDN_gates_executed_and_connected'),'Do not promote an unpowered baseline'
        commands.append('read_db '+tcl(baseline/'routed.odb'));selected=[] if plan=='A_replay' else [focus]
        rec['baseline_routed_odb_sha256']=sha(baseline/'routed.odb')
    for case in selected:
        view_plan=plan if case==focus else 'A';view_plan='A' if view_plan=='A_replay' else view_plan
        source,j,jpath=child_source(case,view_plan);alias='p126_'+case+'_'+view_plan;dest=out/(alias+'.lef')
        clean=source.parent/'clean.odb';assert sha(clean)==j['clean_odb_sha256']
        detailed=out/(case+'.detailed.lef');export=out/(case+'.detail-export.tcl')
        export.write_text('read_db '+tcl(clean)+'\nwrite_abstract_lef -bloat_factor 0 '+tcl(detailed)+'\n')
        with (out/(case+'.detail-export.log')).open('x') as f:er=subprocess.run(common+[IMAGE,BIN,'-threads','1','-no_init','-exit',str(export)],stdout=f,stderr=subprocess.STDOUT)
        assert er.returncode==0,'Actual detailed LEF export failed'
        validation=verify_lef_view(source,detailed)
        (out/(case+'.detail-contract.json')).write_text(json.dumps(validation,indent=2)+'\n')
        alias_view(detailed,dest,contract['physical_instances'][case]['master'],alias)
        views[case]={'source_clean_receipt':str(jpath),'source_clean_receipt_sha256':sha(jpath),'source_abstract_lef':str(source),'source_abstract_sha256':sha(source),'source_clean_odb_sha256':sha(clean),
          'actual_detailed_LEF_sha256':sha(detailed),'detailed_LEF_gate':validation,'parent_alias':alias,'alias_lef_sha256':sha(dest)}
        commands.append('read_lef '+tcl(dest))
    if plan=='A':
        commands += ['read_verilog '+tcl(inputs/'parent.v'),'link_design '+contract['top'],'source '+tcl(inputs/'setup.tcl'),
          'cut_rows -halo_width_x 2 -halo_width_y 2',
          'add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power',
          'add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground','global_connect',
          'set_voltage_domain -name CORE -power VDD -ground VSS','define_pdn_grid -name parent_grid -voltage_domains CORE -pins metal10',
          'add_pdn_stripe -grid parent_grid -layer metal1 -width 0.17 -pitch 2.4 -offset 0 -followpins',
          'add_pdn_stripe -grid parent_grid -layer metal4 -width 0.48 -pitch 56 -offset 2',
          'add_pdn_stripe -grid parent_grid -layer metal7 -width 1.40 -pitch 30 -offset 2',
          'add_pdn_stripe -grid parent_grid -layer metal10 -width 1.40 -pitch 30 -offset 2',
          'add_pdn_connect -grid parent_grid -layers {metal1 metal4}','add_pdn_connect -grid parent_grid -layers {metal4 metal7}',
          'add_pdn_connect -grid parent_grid -layers {metal7 metal10}']
        for i,info in enumerate(contract['physical_instances'].values()):
            commands += ['define_pdn_grid -name macro_pg_'+str(i)+' -voltage_domains CORE -macro -instances '+tcl(info['instance'])+' -grid_over_pg_pins -halo {2 2 2 2}',
              'add_pdn_connect -grid macro_pg_'+str(i)+' -layers {metal7 metal10}']
        commands += ['pdngen -failed_via_report '+tcl(out/'failed_vias.rpt')]
        commands += ['set llhd_macro_instances {'+' '.join(v['instance'] for v in contract['physical_instances'].values())+'}',
          'source '+tcl(DRIVER/'filter_parent_pg.tcl')]
    else:
        inst=contract['physical_instances'][focus]['instance']
        commands += ['set b [ord::get_db_block]','set i [$b findInst '+tcl(inst)+']']
        if plan!='A_replay':commands += ['set m [[ord::get_db] findMaster '+tcl(views[focus]['parent_alias'])+']','if {![$i swapMaster $m]} {error {Physical macro view swap failed}}']
        commands += ['set changednets {};foreach it [$i getITerms] {set n [$it getNet];if {$n ne "NULL" && [$n getSigType] ni {POWER GROUND}} {lappend changednets $n}}',
          'foreach n [lsort -unique $changednets] {set w [$n getWire];if {$w ne "NULL"} {odb::dbWire_destroy $w}}']
    commands += ['create_clock -name parent_route_classification_only -period 2.5 [get_ports clk]']
    setup=out/'run_setup.tcl';setup.write_text('\n'.join(commands)+'\n')
    rec['child_views']=views;rec['routing_only_macro_model']='Not characterized; capacitance zero is only a linker placeholder. Do not use for parent RC/STA/electrical qualification.'
    rec['parent_PDN_strategy']='Detailed bloat0 OBS; parent M1/M4/M7/M10 grid plus direct M7-M10 via stacks. Only unsafe NEW parent via groups are selected out using actual M7/M8/M9/M10 source OBS and conservative 2um landing guard; each table maximum1.5um verified. Original geometry/OBS/pins/rules retained. No M8/M9 PG straps (r04 straps caused actual PSM shorts). Independent native DRC/PSM still mandatory. Freeze checked A PG for all variants.'
    rec['setup_sha256']=sha(setup)
    env='PINXY_PARENT_OUT={},PINXY_PARENT_INPUT={},PINXY_PARENT_RUN_SETUP={},PINXY_DRIVER={},OMP_NUM_THREADS=4'.format(out,inputs,setup,DRIVER)
    cmd=common+['--env',env,IMAGE,BIN,'-threads','4','-no_init','-exit',str(DRIVER/'parent_trial.tcl')];rec['command']=cmd
    with (out/'openroad.log').open('x') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
    rec['returncode']=r.returncode
    expected=json.loads((inputs/'endpoints.json').read_text())
    for prefix in ['before','after']:
        p=out/(prefix+'.endpoints.tsv')
        if p.exists():rec[prefix+'_graph_check']=validate_graph(p,contract,expected)
    if (out/'routed.odb').exists():
        denv='PINXY_DRC_ODB={},PINXY_TOP_LAYER=10,PINXY_DRC_OUT={}'.format(out/'routed.odb',out/'independent.drc')
        with (out/'independent_drc.log').open('x') as f:d=subprocess.run(common+['--env',denv,IMAGE,BIN,'-threads','1','-no_init','-exit',str(DRIVER/'independent_drc.tcl')],stdout=f,stderr=subprocess.STDOUT)
        rec['independent_DRC_returncode']=d.returncode;report=out/'independent.drc'
        rec['independent_DRC_count']=len(re.findall(r'^violation type:',report.read_text(),re.M)) if d.returncode==0 and report.exists() else None
    if (out/'whole_access.tsv.gz').exists():
        rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
        (out/'whole_access.json').write_text(json.dumps(rec['whole_signal_geometry'],indent=2)+'\n')
    stages=list(csv.DictReader((out/'stages.tsv').open(),delimiter='\t'));log=(out/'openroad.log').read_text()
    rec['stages']=stages;rec['PDN_gates_executed_and_connected']=all(any(s['stage']==n and s['status']=='EXECUTED' for s in stages) for n in ['pdn_check_VDD','pdn_check_VSS','pdn_final_VDD','pdn_final_VSS']) and all('All shapes on net '+n+' are connected.' in log for n in ['VDD','VSS'])
    def lines(path):return sorted(path.read_text().splitlines()) if path.exists() else None
    rec['parent_PG_geometry_unchanged_by_signal_route']=lines(out/'before.pdn.tsv') is not None and lines(out/'before.pdn.tsv')==lines(out/'after.pdn.tsv')
    rec['all_instance_master_XY_orient_unchanged_by_signal_route']=lines(out/'before.instances.tsv') is not None and lines(out/'before.instances.tsv')==lines(out/'after.instances.tsv')
    if plan!='A':
        rec['parent_PG_geometry_matches_frozen_A']=lines(out/'before.pdn.tsv') is not None and lines(out/'before.pdn.tsv')==lines(baseline/'before.pdn.tsv')
        rec['TOP_IO_all_pin_boxes_match_frozen_A']=lines(out/'before.pins.tsv') is not None and lines(out/'before.pins.tsv')==lines(baseline/'before.pins.tsv')
        def family_placements(path):
            if not path.exists():return None
            result=[]
            with path.open() as f:
                for row in csv.DictReader(f,delimiter='\t'):
                    for case,info in contract['physical_instances'].items():
                        if row['instance']==info['instance']:
                            assert row['master'].startswith('p126_'+case+'_')
                            row['master']='UNCHANGED_LOGICAL_LEAF_FAMILY_'+case
                    result.append(tuple(row[k] for k in ['instance','master','x','y','orientation']))
            return sorted(result)
        rec['all_leaf_families_and_constant_cells_XY_match_frozen_A']=family_placements(out/'before.instances.tsv') is not None and family_placements(out/'before.instances.tsv')==family_placements(baseline/'before.instances.tsv')
    rec['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'}
    passed=rec.get('independent_DRC_count')==0 and rec.get('whole_signal_geometry',{}).get('pass') and rec['PDN_gates_executed_and_connected'] and r.returncode==0 and rec['parent_PG_geometry_unchanged_by_signal_route'] and rec['all_instance_master_XY_orient_unchanged_by_signal_route']
    if plan!='A':passed=passed and rec['parent_PG_geometry_matches_frozen_A'] and rec['TOP_IO_all_pin_boxes_match_frozen_A'] and rec['all_leaf_families_and_constant_cells_XY_match_frozen_A']
    rec['status']='NATIVE_ACCESS_GATES_PASSED_NOT_FULL_QUALIFICATION' if passed else 'ACTUAL_PARENT_ACCESS_FAILED_OR_INCOMPLETE'
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    print('NEW_PARENT_RESULT',design,focus,plan,rec.get('independent_DRC_count'),rec.get('whole_signal_geometry',{}).get('pass'),rec['PDN_gates_executed_and_connected'],flush=True)
    return bool(passed)

if __name__=='__main__':
    inputs=ROOT/'inputs'/sys.argv[1];rev=sys.argv[2];plans=sys.argv[3:] or ['A','A_replay','A_child_replay','Aopt','B','C']
    results=[]
    for plan in plans:
        try:results.append(one(inputs,rev,plan))
        except Exception:
            traceback.print_exc();c=json.loads((inputs/'contract.json').read_text());out=ROOT/'parents'/rev/(c['design']+'-'+c['focus']+'-'+plan);out.mkdir(parents=True,exist_ok=True)
            (out/'driver_failure.json').write_text(json.dumps({'status':'DRIVER_OR_BASELINE_GATE_FAILED_NOT_A_PASS','traceback':traceback.format_exc()},indent=2)+'\n')
            results.append(False)
    sys.exit(0 if all(results) else 1)
