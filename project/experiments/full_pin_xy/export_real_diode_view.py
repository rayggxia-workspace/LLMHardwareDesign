"""Real routed 658-diode GEMM physical/RC timing views; never full qualification."""
from pathlib import Path
import csv,datetime,json,os,re,shutil,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from lef_view_contract import parse,verify

DRIVER=Path(__file__).resolve().parent


def run(revision):
    source=ROOT/'antenna_incremental_eco/r01/gemm-C';receipt=source/'execution.json';j=json.loads(receipt.read_text())
    out=ROOT/'diode_views'/revision/'gemm-C';out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'REAL_658_DIODE_ACCESS_AND_EXTRACTED_RESEARCH_VIEW_NOT_FULL_QUALIFICATION',
      'full_qualification':False,'source_receipt':str(receipt),'source_receipt_SHA256':sha(receipt),
      'original_M5_M6_pins_not_raised':True,'complete_rules_and_RTL_formal':'NOT_QUALIFIED',
      'scheduler_job':os.environ['SLURM_JOB_ID'],'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip()}
    try:
        assert j.get('completed_utc') and j['native_returncodes']['implementation']==j['native_returncodes']['fresh_DRC']==0
        assert j['fresh_DRC_count']==0 and j['whole_signal_geometry']['pass'] and j['actual_total_real_diodes']==658
        assert j['all_original_instances_and_signal_graph_preserved_with_only_22_real_diode_loads']
        assert j['all_prior_functional_and_636_diode_poses_and_terminals_unchanged'] and all(j['pin_PG_die_unchanged'].values())
        assert j['all_sources_unchanged']
        assert all(j['native_stage_status'].get(s)=='EXECUTED' for s in ['detailed_route','preserve_original_views','VDD','VSS','whole_signal_geometry','rcx','sta'])
        original=ROOT/'eco_views/r02/gemm-C';old=json.loads((original/'execution.json').read_text())
        assert sha(original/'abstract.lef')==old['files']['abstract.lef']['sha256']
        assert sha(original/'pins.tsv')==old['files']['pins.tsv']['sha256']
        trial=ROOT/'trials/access-r03/gemm-C/execution.json';baseline=json.loads(trial.read_text());sdc=Path(baseline['source_sdc'])
        assert sha(sdc)==baseline['input_sha256'][str(sdc)]
        odb=source/'routed.odb';spef=source/'extracted.spef'
        for p in [odb,spef,source/'independent.drc']:assert sha(p)==j['files'][p.name]['sha256']
        inputs={str(p):sha(p) for p in [receipt,odb,spef,original/'execution.json',original/'abstract.lef',original/'pins.tsv',trial,sdc]}
        rec.update({'source_SHA':inputs,'source_geometry_sha256':sha(odb),'source_SPEF_sha256':sha(spef),
          'source_native_DRC':0,'source_setup_ns':j['setup_ns'],'source_hold_ns':j['hold_ns'],
          'source_literal_violated_markers':j.get('literal_VIOLATED_markers_not_complete_failure_count'),
          'separate_additional_diode_cost':j['separate_additional_diode_cost']})
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
        script=out/'export.tcl';script.write_text('\n'.join(lines)+'\n')
        rec['native_export_returncode']=execute(common,script,out/'export.log')
        assert rec['native_export_returncode']==0
        rec['detailed_OBS_view_contract']=verify(out/'abstract.lef',out/'detailed.lef')
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
        assert {p:d for p,d in pins.items() if p in expected}==expected and len(expected)==3753
        rec['matching_all_signal_model_pins']=3753
        rec['minimum_period_present']='minimum_period' in (out/'timing.lib').read_text()
        rec['all_sources_and_pre_RCX_geometry_unchanged']=all(sha(Path(p))==v for p,v in inputs.items()) and sha(out/'clean.odb')==sha(odb)
        assert rec['all_sources_and_pre_RCX_geometry_unchanged']
        rec['status']='ACTUAL_REAL_DIODE_VIEW_EXPORTED_NOT_QUALIFIED_COMMON_BASE_OR_FULL_SYSTEM'
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return 0 if 'actual_failure' not in rec and rec.get('matching_all_signal_model_pins')==3753 else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
