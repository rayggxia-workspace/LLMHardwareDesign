"""Independent parent RC/STA after physical gates, using exact real leaf models.

Never analyzes routing-only zero-capacity stubs, never exports a physical ODB
after RCX. This NEW 2.5ns controlled benchmark has incomplete external models,
missing minimum-period coverage and unqualified SRAM/GDS; no system signoff.
"""
from pathlib import Path
import datetime,json,os,re,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,BIN,sha
from run_parent_trial import tcl

DRIVER=Path(__file__).resolve().parent

def alias_lib(source,destination,alias):
    text=source.read_text();lib=re.search(r'(?m)^\s*library\s*\(\s*([^\)]+)\)',text);cell=re.search(r'(?m)^\s*cell\s*\(\s*([^\)]+)\)',text)
    assert lib and cell
    text,n=re.subn(r'(?m)^(\s*library\s*\()\s*[^\)]+\)',lambda m:m[1]+alias+'_extracted_model)',text);assert n==1
    text,n=re.subn(r'(?m)^(\s*cell\s*\()\s*[^\)]+\)',lambda m:m[1]+alias+')',text);assert n==1
    destination.write_text(text)
    return {'source_library_declaration':lib[1],'source_cell_declaration':cell[1],'alias':alias,'only_library_and_cell_declarations_renamed':True}

def one(parent_rev,design,focus,plan,revision):
    source=ROOT/'parents'/parent_rev/(design+'-'+focus+'-'+plan)
    out=ROOT/'parent_rc_sta'/revision/(design+'-'+focus+'-'+plan)
    if out.exists():raise RuntimeError('Refuse existing parent analysis directory: '+str(out))
    out.mkdir(parents=True)
    rec={'scope':'NEW_CONTROLLED_PARENT_SCOPED_RC_STA_NOT_SYSTEM_QUALIFICATION','source_parent_directory':str(source),
      'design':design,'focus':focus,'plan':plan,'source_parent_revision':parent_rev,'scheduler_job':os.environ['SLURM_JOB_ID'],
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'full_system_RC_STA_electrical_qualified':False,'limitations':['NEW fixed 2.5ns parent benchmark, not historical constraints','external input driver/slew and output load absent, explicitly incomplete',
        'leaf internal STA/electrical failures remain separate mandatory failures','native exported models lack minimum_period coverage','research SRAM models and missing GDS/LVS, no characterized signoff library','RCX serialization issue isolated; absolute RC needs independent corroboration']}
    receipt=source/'execution.json';p=json.loads(receipt.read_text()) if receipt.exists() else {}
    rec['parent_execution_sha256']=sha(receipt) if receipt.exists() else None
    if not (p.get('status')=='NATIVE_ACCESS_GATES_PASSED_NOT_FULL_QUALIFICATION' and p.get('finished_utc') and p.get('independent_DRC_count')==0 and p.get('whole_signal_geometry',{}).get('pass') and p.get('PDN_gates_executed_and_connected')):
        rec.update({'status':'RC_STA_NOT_EXECUTED_INPUT_PHYSICAL_GATE_FAILED_OR_INCOMPLETE','actual_parent_status':p.get('status'),'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
        (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');print('PARENT_RC_STA_REFUSED_PHYSICAL_INPUT',source,flush=True);return False
    baseline=json.loads((ROOT/'parents'/parent_rev/(design+'-'+focus+'-A')/'execution.json').read_text())
    views=dict(baseline['child_views']);views.update(p['child_views'])
    models={};commands=['read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib']
    for case,view in views.items():
        variant='C' if case==focus and plan=='C' else 'A'
        if case==focus and plan not in ['A','A_replay','C']:
            rec.update({'status':'RC_STA_NOT_EXECUTED_MATCHING_CHANGED_CHILD_MODEL_NOT_EXPORTED','missing_model_for_plan':plan,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
            (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');return False
        directory=ROOT/'leaf_timing_models/r02'/(case+'-'+variant);model=json.loads((directory/'execution.json').read_text())
        assert model['status']=='NATIVE_EXTRACTED_MODEL_EXPORTED_NOT_QUALIFIED' and model['exact_all_signal_pin_direction_match'] and model['SPEF_replay_matches_recorded_trial_1e_minus5_ns']
        assert model['model_has_timing_groups'] and model['clean_odb_sha256']==view['source_clean_odb_sha256']
        assert sha(directory/'timing.lib')==model['generated_library_sha256']
        alias=view['parent_alias'];target=out/(alias+'.lib');change=alias_lib(directory/'timing.lib',target,alias)
        models[case]={'source_receipt':str(directory/'execution.json'),'receipt_sha256':sha(directory/'execution.json'),'source_lib_sha256':sha(directory/'timing.lib'),
          'alias_lib_sha256':sha(target),'declaration_only_alias':change,'minimum_period_present':model['minimum_period_present'],'leaf_source_checks_sha256':model['source_timing_checks_sha256'],
          'leaf_replayed_setup_hold':model['SPEF_replay_worst_slack'],'leaf_reported_violator_rows':sum('(VIOLATED)' in s for s in (directory/'checks.txt').read_text().splitlines())}
        commands.append('read_liberty '+tcl(target))
    odb=source/'routed.odb';before=sha(odb);assert before==p['files']['routed.odb']['sha256']
    rec['input_physical_odb_sha256']=before;rec['actual_leaf_models']=models
    rec['retained_leaf_timing_or_electrical_failures']=any(q['leaf_reported_violator_rows']>0 for q in models.values())
    commands += ['read_db '+tcl(odb),'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl',
      'create_clock -name new_controlled_parent_benchmark -period 2.5 [get_ports clk]',
      'set_propagated_clock [all_clocks]','define_process_corner -ext_model_index 0 X',
      'set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules','extract_parasitics',
      'write_spef '+tcl(out/'extracted.spef'),'read_spef '+tcl(out/'extracted.spef'),
      'report_worst_slack -max -digits 6 > '+tcl(out/'setup.txt'),'report_worst_slack -min -digits 6 > '+tcl(out/'hold.txt'),
      'report_tns -max -digits 6 > '+tcl(out/'setup_tns.txt'),'report_tns -min -digits 6 > '+tcl(out/'hold_tns.txt'),
      'report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > '+tcl(out/'checks.txt'),
      'check_setup -verbose > '+tcl(out/'constraint_coverage.txt'),'report_parasitic_annotation -report_unannotated > '+tcl(out/'parasitic_coverage.txt'),
      'report_checks -path_delay min_max -fields {capacitance slew fanout} -format json -group_path_count 100 -endpoint_path_count 1 > '+tcl(out/'sample_paths.json')]
    script=out/'analysis.tcl';script.write_text('\n'.join(commands)+'\n')
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
      '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro','--home',str(ROOT/'home'),'--pwd',str(out)]
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    with (out/'analysis.log').open('x') as f:r=subprocess.run(common+[IMAGE,BIN,'-threads','4','-no_init','-exit',str(script)],stdout=f,stderr=subprocess.STDOUT)
    rec['native_returncode']=r.returncode;rec['physical_input_unchanged']=sha(odb)==before
    rec['physical_ODB_written_after_RCX']=False;rec['timing_electrical_violator_rows']=sum('(VIOLATED)' in s for s in (out/'checks.txt').read_text().splitlines()) if (out/'checks.txt').exists() else None
    for kind in ['setup','hold']:
        m=re.search(r'worst slack (?:max|min)\s+([-\d.]+)',(out/(kind+'.txt')).read_text()) if (out/(kind+'.txt')).exists() else None
        rec[kind+'_worst_slack_ns']=float(m[1]) if m else None
    rec['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={q.name:{'bytes':q.stat().st_size,'sha256':sha(q)} for q in out.iterdir() if q.is_file() and q.name!='execution.json'}
    rec['status']='SCOPED_PARENT_RC_STA_EXECUTED_NOT_QUALIFIED' if r.returncode==0 and rec['physical_input_unchanged'] else 'ACTUAL_SCOPED_PARENT_ANALYSIS_FAILED'
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');print('SCOPED_PARENT_RC_STA',design,focus,plan,rec['status'],flush=True)
    return r.returncode==0 and rec['physical_input_unchanged']

if __name__=='__main__':
    parent_rev,design,focus,revision=sys.argv[1:5];results=[]
    for plan in sys.argv[5:] or ['A','A_replay','C']:
        out=ROOT/'parent_rc_sta'/revision/(design+'-'+focus+'-'+plan)
        if out.exists():
            print('REFUSE_EXISTING_PARENT_ANALYSIS_DIRECTORY_UNCHANGED',out,flush=True);results.append(False);continue
        try:results.append(one(parent_rev,design,focus,plan,revision))
        except Exception:
            traceback.print_exc();out=ROOT/'parent_rc_sta'/revision/(design+'-'+focus+'-'+plan)
            if not out.exists():out.mkdir(parents=True)
            failure=out/'driver_failure.json'
            if not failure.exists():failure.write_text(json.dumps({'status':'ACTUAL_PARENT_ANALYSIS_DRIVER_FAILURE','traceback':traceback.format_exc()},indent=2)+'\n')
            results.append(False)
    sys.exit(0 if all(results) else 1)
