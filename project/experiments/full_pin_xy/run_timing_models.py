"""Export real leaf timing models from matching clean ODB + existing SPEF.

Reuse the project's write_timing_model flow, without modifying active parents.
These are extracted research models, not characterized SRAM/signoff libraries.
Missing boundary models, minimum-period arcs and baseline failures stay visible.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import csv,datetime,json,os,re,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,BIN,sha
from run_parent_trial import BASE,C_REVISION,tcl

DRIVER=Path(__file__).resolve().parent

def one(case,variant,revision):
    rev,plan=(BASE[case],'A') if variant=='A' else (('grid-r05','C') if case=='llaccel_aux' else (C_REVISION[case],'C'))
    clean=ROOT/'finalized'/rev/(case+'-'+plan);proof=json.loads((clean/'execution.json').read_text())
    assert proof['independent_DRC_count']==0 and proof['whole_access']['pass'] and proof['clean_byte_identical_to_pre_RCX_source']
    trial=Path(proof['legacy_RC_STA_receipt']);j=json.loads(trial.read_text());odb=clean/'clean.odb';spef=trial.parent/'extracted.spef';sdc=Path(j['source_sdc'])
    assert sha(odb)==proof['clean_odb_sha256'] and sha(spef)==j['outputs']['extracted.spef']['sha256']
    assert sha(sdc)==j['input_sha256'][str(sdc)]
    out=ROOT/'leaf_timing_models'/revision/(case+'-'+variant);out.mkdir(parents=True,exist_ok=False)
    selected=j.get('selected_pin_count')
    if selected is None:
        env=dict(s.split('=',1) for s in j['command'][j['command'].index('--env')+1].split(','))
        selected=sum(s.startswith('lappend relocations ') for s in Path(env['PINXY_RELOCATIONS']).read_text().splitlines())
    rec={'case':case,'variant':variant,'physical_revision':rev,'source_plan':plan,'selected_pin_count':selected,
      'source_clean_receipt':str(clean/'execution.json'),'source_clean_receipt_sha256':sha(clean/'execution.json'),
      'source_trial_receipt':str(trial),'source_trial_receipt_sha256':sha(trial),'clean_odb_sha256':sha(odb),'matching_existing_SPEF_sha256':sha(spef),'source_SDC_sha256':sha(sdc),
      'source_timing_checks_sha256':j['outputs']['timing.checks.txt']['sha256'],'source_boundary_models':'INCOMPLETE_INHERITED; no silently added load/slew/driver assumptions',
      'scope':'Native extracted research leaf timing model, not a port-only stub, NOT characterized SRAM or complete physical/system timing qualification; llaccel SYSTEM C is 8-pin pilot only',
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
      'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    lines=['read_liberty '+tcl(p) for p in j['libs']]
    lines += ['read_db '+tcl(odb),'read_sdc '+tcl(sdc),'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl','read_spef '+tcl(spef),
      'report_worst_slack -max -digits 6 > '+tcl(out/'setup.txt'),'report_worst_slack -min -digits 6 > '+tcl(out/'hold.txt'),
      'report_parasitic_annotation -report_unannotated > '+tcl(out/'parasitic_coverage.txt'),
      'check_setup -verbose > '+tcl(out/'constraint_coverage.txt'),
      'report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > '+tcl(out/'checks.txt'),
      'write_timing_model '+tcl(out/'timing.lib'),
      'set f [open '+tcl(out/'native_library_sha256.txt')+' w]']
    for p in j['libs']:lines.append('puts $f [exec sha256sum '+tcl(p)+']')
    lines += ['puts $f [exec sha256sum /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad]','close $f']
    script=out/'export.tcl';script.write_text('\n'.join(lines)+'\n')
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
      '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro','--home',str(ROOT/'home'),'--pwd',str(out)]
    with (out/'export.log').open('x') as f:r=subprocess.run(common+[IMAGE,BIN,'-threads','4','-no_init','-exit',str(script)],stdout=f,stderr=subprocess.STDOUT)
    rec['native_export_returncode']=r.returncode
    replay={}
    for kind in ['setup','hold']:
        old=re.search(r'worst slack (?:max|min)\s+([-\d.]+)',(trial.parent/('timing.'+kind+'.txt')).read_text())
        new=re.search(r'worst slack (?:max|min)\s+([-\d.]+)',(out/(kind+'.txt')).read_text()) if (out/(kind+'.txt')).exists() else None
        replay[kind]={'original_trial_ns':float(old[1]) if old else None,'SPEF_replay_ns':float(new[1]) if new else None,
          'delta_ns':float(new[1])-float(old[1]) if old and new else None}
    rec['SPEF_replay_worst_slack']=replay
    rec['SPEF_replay_matches_recorded_trial_1e_minus5_ns']=all(q['delta_ns'] is not None and abs(q['delta_ns'])<=1e-5 for q in replay.values())
    if r.returncode==0 and (out/'timing.lib').exists():
        check=out/'check.tcl';check.write_text('read_liberty '+tcl(out/'timing.lib')+'\nset f [open '+tcl(out/'model_pins.tsv')+' w]\nputs $f "pin\\tdirection"\nforeach p [get_lib_pins -of_objects [get_lib_cells *]] {puts $f "[get_full_name $p]\\t[get_property $p direction]"}\nclose $f\n')
        with (out/'check.log').open('x') as f:r2=subprocess.run(common+[IMAGE,BIN,'-threads','1','-no_init','-exit',str(check)],stdout=f,stderr=subprocess.STDOUT)
        rec['fresh_model_read_returncode']=r2.returncode
        if r2.returncode==0:
            with (clean/'pins.tsv').open() as f:physical=list(csv.DictReader(f,delimiter='\t'))
            expected={q['pin'].replace('\\',''):q['direction'].lower() for q in physical if q['use'] not in ['POWER','GROUND']}
            pg={q['pin'].replace('\\','') for q in physical if q['use'] in ['POWER','GROUND']}
            with (out/'model_pins.tsv').open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
            allpins={q['pin'].split('/')[-1].replace('\\',''):q['direction'].lower() for q in rows};assert len(allpins)==len(rows),'Ambiguous model pin names'
            aggregates={}
            for name in set(allpins)-set(expected)-pg:
                members=[p for p in expected if re.fullmatch(re.escape(name)+r'\[\d+\]',p)]
                assert len(members)>1 and all(expected[p]==allpins[name] for p in members),('Unknown extra native model port',name)
                aggregates[name]={'actual_native_direction':allpins[name],'members':sorted(members)}
            got={p:d for p,d in allpins.items() if p in expected}
            rec['native_bus_aggregate_declarations_not_extra_bits']=aggregates
            rec['native_PG_ports_not_signal_pins']=sorted(pg & set(allpins))
            rec['exact_all_signal_pin_direction_match']=got==expected;rec['actual_model_signal_pins']=len(got);rec['expected_physical_signal_pins']=len(expected)
        text=(out/'timing.lib').read_text();rec['model_has_timing_groups']='timing (' in text or 'timing(' in text
        rec['minimum_period_present']='minimum_period' in text;rec['generated_library_sha256']=sha(out/'timing.lib')
        rec['model_file_bytes']=(out/'timing.lib').stat().st_size
    rec['source_odb_and_SPEF_unchanged']=sha(odb)==rec['clean_odb_sha256'] and sha(spef)==rec['matching_existing_SPEF_sha256']
    rec['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in out.iterdir() if p.is_file() and p.name!='execution.json'}
    rec['status']='NATIVE_EXTRACTED_MODEL_EXPORTED_NOT_QUALIFIED' if rec.get('exact_all_signal_pin_direction_match') and rec['SPEF_replay_matches_recorded_trial_1e_minus5_ns'] else 'ACTUAL_MODEL_EXPORT_INTERFACE_OR_SPEF_REPLAY_CHECK_FAILED'
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    print('LEAF_MODEL',case,variant,rec['status'],rec.get('actual_model_signal_pins'),flush=True)
    return rec

def safe(args):
    try:return one(*args)
    except Exception:
        traceback.print_exc();out=ROOT/'leaf_timing_models'/args[2]/(args[0]+'-'+args[1]);out.mkdir(parents=True,exist_ok=True)
        (out/'driver_failure.json').write_text(json.dumps({'status':'FAILED_NOT_A_MODEL_PASS','traceback':traceback.format_exc()},indent=2)+'\n')

if __name__=='__main__':
    assert int(os.environ['SLURM_CPUS_PER_TASK'])>=8
    rev=sys.argv[1];cases=sys.argv[2:] or ['act','gemm','mxu','vector','opentpu_aux','llaccel_aux']
    results=[]
    for case in cases:
        with ThreadPoolExecutor(max_workers=2) as pool:results.extend(pool.map(safe,[(case,p,rev) for p in ['A','C']]))
    sys.exit(0 if all(q and q['status']=='NATIVE_EXTRACTED_MODEL_EXPORTED_NOT_QUALIFIED' for q in results) else 1)
