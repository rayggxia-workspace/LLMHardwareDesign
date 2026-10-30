"""Real independent Nangate45 64x64 1r1w/mask1 physical feasibility trial.

This is not the original fake SRAM and never replaces its views. Actual
behavior/latency, dimensions, target layers and cost require separate review.
"""
from pathlib import Path
import csv,datetime,json,os,re,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,BIN,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from check_access import check

DRIVER=Path(__file__).resolve().parent


def run(revision):
    probe=ROOT/'native_ram_capability/r01/execution.json';p=json.loads(probe.read_text())
    assert p.get('completed_utc') and p['native_probe_returncode']==0 and p['generate_ram_present']
    out=ROOT/'native_ram_physical_trial'/revision/'64x64-1r1w-mask1';out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'REAL_STANDARD_CELL_RAM_GENERATION_NOT_ORIGINAL_SRAM_REPLACEMENT_OR_FULL_QUALIFICATION',
      'full_qualification':False,'existing_reference_leafs_or_macro_views_modified':False,
      'requested_memory':{'words':64,'word_size':64,'rw_ports':0,'read_ports':1,'write_ports':1,'mask_size_bits':1,'storage_cell':'DFF_X1'},
      'RAM_implementation':'Experimental installed native generate_ram; actual standard cells and wires, not a placeholder GDS',
      'original_fake_macro_compatibility':'NOT_VERIFIED_FUNCTION_READ_ENABLE_LATENCY_COLLISION_PIN_LAYER_SIZE_OUTLINE_COST',
      'paired_comparison_integration':'NOT_EXECUTED','RC_STA':'NOT_EXECUTED_UNTIL_SEMANTIC_AND_INTERFACE_AUDIT',
      'source_SHA':{str(probe):sha(probe)},'scheduler_job':os.environ['SLURM_JOB_ID'],
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'native_returncodes':{}}
    save=lambda:(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    save();common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    try:
        rec['actual_OpenROAD_binary_SHA256']=subprocess.check_output(common+[IMAGE,'sha256sum',BIN]).decode().split()[0]
        lib='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
        rec['actual_Liberty_SHA256']=subprocess.check_output(common+[IMAGE,'sha256sum',lib]).decode().split()[0]
        assert rec['actual_OpenROAD_binary_SHA256']==p['actual_OpenROAD_binary_SHA256'] and rec['actual_Liberty_SHA256']==p['actual_Liberty_SHA256']
        helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
        lines=[helper,'read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef',
          'read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef','read_liberty '+tcl(lib),
          'set fillers {};foreach l [[ord::get_db] getLibs] {foreach m [$l getMasters] {if {[$m getType] eq "CORE_SPACER"} {lappend fillers [$m getName]}}};if {![llength $fillers]} {error "Actual standard-cell fillers missing"}',
          'if {![stage real_native_RAM_generation {generate_ram -word_size 64 -num_words 64 -rw_ports 0 -r_ports 1 -w_ports 1 -mask_size 1 -storage_cell DFF_X1 -routing_layer {metal1 0.14} -ver_layer {metal2 0.14 4.2} -hor_layer {metal3 0.14 4.2} -filler_cells $fillers -write_behavioral_verilog '+tcl(out/'generated_behavioral.v')+'}]} {catch {write_db '+tcl(out/'failed_generation.odb')+'};close $stages;exit 1}',
          'write_db '+tcl(out/'actual_generated_NOT_QUALIFIED.odb'),'write_def '+tcl(out/'actual_generated.def'),
          'write_verilog '+tcl(out/'actual_structural.v'),'write_abstract_lef -bloat_factor 0 '+tcl(out/'actual_generated.lef'),
          'fingerprint '+tcl(out/'actual'),
          'set b [ord::get_db_block];set r [$b getDieArea];set f [open '+tcl(out/'actual_design.tsv')+' w];puts $f [join [list [$b getName] [$b getDbUnitsPerMicron] [$r xMin] [$r yMin] [$r xMax] [$r yMax] [llength [$b getInsts]] [llength [$b getBTerms]]] "\t"];close $f',
          'stage VDD {check_power_grid -net VDD -error_file '+tcl(out/'VDD.rpt')+'}',
          'stage VSS {check_power_grid -net VSS -error_file '+tcl(out/'VSS.rpt')+'}',
          'stage whole_signal_geometry {source '+tcl(DRIVER/'export_access.tcl')+'}','close $stages']
        script=out/'generate.tcl';script.write_text('\n'.join(lines)+'\n')
        env='PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz')
        rec['native_returncodes']['real_generation']=execute(common,script,out/'native.log',env,threads=4);save()
        if (out/'actual_generated_NOT_QUALIFIED.odb').exists():
            script=out/'fresh.tcl';script.write_text('read_db '+tcl(out/'actual_generated_NOT_QUALIFIED.odb')+'\nset_routing_layers -signal metal2-metal10 -clock metal4-metal10\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
            rec['native_returncodes']['independent_DRC']=execute(common,script,out/'independent.log',threads=1)
            if rec['native_returncodes']['independent_DRC']==0:rec['native_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
        if (out/'whole_access.tsv.gz').exists():rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
        if (out/'actual_design.tsv').exists():rec['actual_design_row']=(out/'actual_design.tsv').read_text().strip().split('\t')
        if (out/'stages.tsv').exists():
            with (out/'stages.tsv').open() as f:rec['native_stage_status']={r['stage']:r['status'] for r in csv.DictReader(f,delimiter='\t')}
    except Exception:rec['actual_failure']=traceback.format_exc();traceback.print_exc()
    rec['all_sources_unchanged']=all(sha(Path(f))==s for f,s in rec['source_SHA'].items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={f.name:{'bytes':f.stat().st_size,'sha256':sha(f)} for f in out.iterdir() if f.is_file() and f.name!='execution.json'};save()
    return 0 if rec.get('native_DRC_count')==0 and rec.get('whole_signal_geometry',{}).get('pass') and rec['all_sources_unchanged'] and all(rec.get('native_stage_status',{}).get(k)=='EXECUTED' for k in ['real_native_RAM_generation','VDD','VSS','whole_signal_geometry']) else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
