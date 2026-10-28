"""Export access/timing views from completed costed ECO; never promote full qualification."""
from pathlib import Path
import csv,datetime,json,os,re,shutil,sys
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from lef_view_contract import parse,verify

DRIVER=Path(__file__).resolve().parent


def run(case,source_revision,view_revision):
    assert case in ['gemm','mxu']
    source=ROOT/'leaf_eco'/source_revision/(case+'-C');receipt=source/'execution.json';j=json.loads(receipt.read_text())
    assert j.get('completed_utc') and j['native_returncode']==0 and j['fresh_DRC_returncode']==0 and j['fresh_DRC_count']==0
    assert j['whole_signal_geometry']['pass'] and j['source_unchanged'] and all(j['geometry_invariants'].values())
    assert j['full_qualification'] is False and j['targeted_master_changes']
    assert all(sha(Path(p))==v for p,v in j['source_inputs_SHA'].items())
    original=ROOT/'finalized'/j['source_physical_revision']/(case+'-C');old=json.loads((original/'execution.json').read_text())
    trial=Path(old['legacy_RC_STA_receipt']);baseline=json.loads(trial.read_text());sdc=Path(baseline['source_sdc'])
    assert sha(sdc)==baseline['input_sha256'][str(sdc)]
    odb=source/'routed.odb';spef=source/'extracted.spef'
    for p in [odb,spef,source/'independent.drc']:assert sha(p)==j['files'][p.name]['sha256']
    out=ROOT/'eco_views'/view_revision/(case+'-C');out.mkdir(parents=True,exist_ok=False)
    shutil.copy2(str(odb),str(out/'clean.odb'));assert sha(out/'clean.odb')==sha(odb)
    lines=['read_liberty '+tcl(p) for p in baseline['libs']]
    lines+=['read_db '+tcl(out/'clean.odb'),
      'write_abstract_lef '+tcl(out/'abstract.lef'),'write_abstract_lef -bloat_factor 0 '+tcl(out/'detailed.lef'),
      'write_def '+tcl(out/'clean.def'),'write_verilog '+tcl(out/'clean.v'),
      'set b [ord::get_db_block];set f [open '+tcl(out/'pins.tsv')+' w];puts $f "pin\\tdirection\\tuse\\tnet\\tlayer\\tx0\\ty0\\tx1\\ty1";foreach p [$b getBTerms] {foreach bp [$p getBPins] {foreach r [$bp getBoxes] {puts $f [join [list [$p getName] [$p getIoType] [$p getSigType] [[$p getNet] getName] [[$r getTechLayer] getName] [$r xMin] [$r yMin] [$r xMax] [$r yMax]] "\\t"]}}};close $f',
      'read_sdc '+tcl(sdc),'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl','read_spef '+tcl(spef),
      'report_worst_slack -max -digits 6 > '+tcl(out/'setup.txt'),'report_worst_slack -min -digits 6 > '+tcl(out/'hold.txt'),
      'report_parasitic_annotation -report_unannotated > '+tcl(out/'parasitic_coverage.txt'),
      'check_setup -verbose > '+tcl(out/'constraint_coverage.txt'),'write_timing_model '+tcl(out/'timing.lib'),
      'puts "COSTED_ECO_PHYSICAL_AND_EXTRACTED_RESEARCH_VIEW_EXPORTED_NOT_QUALIFIED"']
    script=out/'export.tcl';script.write_text('\n'.join(lines)+'\n')
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
            '--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
            '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
            '--home',str(ROOT/'home'),'--pwd',str(out)]
    for p in baseline['libs']:
        if Path(p).is_file():common+=['--bind',p+':'+p+':ro']
    rec={'scope':'COSTED_ECO_ACCESS_AND_EXTRACTED_RESEARCH_TIMING_VIEW_NOT_FULL_PHYSICAL_QUALIFICATION',
         'case':case,'source_revision':source_revision,'source_receipt':str(receipt),'source_receipt_sha256':sha(receipt),
         'source_geometry_sha256':sha(odb),'source_SPEF_sha256':sha(spef),'source_SDC_sha256':sha(sdc),
         'source_native_DRC':0,'source_whole_signal_geometry':{k:v for k,v in j['whole_signal_geometry'].items() if k!='nets'},
         'separate_cell_ECO_cost':j['separate_cell_ECO_cost'],'design_formal_equivalence':'NOT_EXECUTED',
         'complete_manufacturing_rules':'NOT_PASSED','missing_exact_SRAM_GDS':case=='mxu','full_qualification':False,
         'scheduler_job':os.environ['SLURM_JOB_ID'],'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip()}
    cost=[]
    for name in ['before.cell_cost.tsv','after.cell_cost.tsv']:
        p=source/name;assert sha(p)==j['files'][name]['sha256']
        with p.open() as f:cost.append({r['instance']:r['type'] for r in csv.DictReader(f,delimiter='\t')})
    a,b=cost
    rec['separate_cell_ECO_cost']['added_functional_instances_excluding_fillers']=sum(b[n]!='CORE_SPACER' for n in set(b)-set(a))
    rec['separate_cell_ECO_cost']['removed_functional_instances_excluding_fillers']=sum(a[n]!='CORE_SPACER' for n in set(a)-set(b))
    rec['separate_cell_ECO_cost']['added_CORE_SPACER_fillers']=sum(b[n]=='CORE_SPACER' for n in set(b)-set(a))
    rec['started_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    rec['native_export_returncode']=execute(common,script,out/'export.log')
    if rec['native_export_returncode']==0:
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
        expected={r['pin'].replace('\\',''):r['direction'].lower() for r in physical if r['use'] not in ['POWER','GROUND']}
        pg={r['pin'].replace('\\','') for r in physical if r['use'] in ['POWER','GROUND']}
        with (out/'model_pins.tsv').open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
        allpins={r['pin'].split('/')[-1].replace('\\',''):r['direction'].lower() for r in rows};assert len(allpins)==len(rows)
        for extra in set(allpins)-set(expected)-pg:
            members=[p for p in expected if re.fullmatch(re.escape(extra)+r'\[\d+\]',p)]
            assert len(members)>1 and all(expected[p]==allpins[extra] for p in members)
        assert {p:d for p,d in allpins.items() if p in expected}==expected
        rec['matching_all_signal_model_pins']=len(expected)
        rec['minimum_period_present']='minimum_period' in (out/'timing.lib').read_text()
    rec['pre_RCX_geometry_and_all_sources_unchanged']=sha(out/'clean.odb')==sha(odb)==rec['source_geometry_sha256'] and sha(spef)==rec['source_SPEF_sha256'] and sha(receipt)==rec['source_receipt_sha256']
    assert rec['pre_RCX_geometry_and_all_sources_unchanged']
    rec['files']={p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in out.iterdir() if p.is_file()}
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    print('COSTED_ECO_VIEW_EXPORTED',case,rec['native_export_returncode'],rec.get('matching_all_signal_model_pins'),'NOT_QUALIFIED',flush=True)
    return rec['native_export_returncode']


if __name__=='__main__':sys.exit(run(*sys.argv[1:4]))
