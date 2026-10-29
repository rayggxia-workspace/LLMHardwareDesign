"""Current MXU parent RC/STA using its exact real extracted macro model.

Same explicitly new research I/O policy as ACT fixtures, not historical parent
constraints or full-system signoff. Zero-length/unannotated nets stay visible.
"""
from pathlib import Path
import datetime,json,os,re,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,BIN,sha
from run_parent_trial import tcl
from run_escape_fixture import execute

DRIVER=Path(__file__).resolve().parent


def run(revision):
    source=ROOT/'mxu_actual_tip_parent/r01/mxu-C';rp=source/'execution.json';q=json.loads(rp.read_text())
    assert q.get('completed_utc') and q['fresh_DRC_count']==0 and q['whole_parent_signal_geometry']['pass'] and q['all_closed_sources_unchanged']
    assert q['new_macro_contract_persisted_and_independently_read_back'] and q['all_macro_functions_layers_sizes_directions_networks_and_clock_USE_preserved_with_exactly_one_authorized_XY_change']
    assert q['native_stage_status']['VDD']==q['native_stage_status']['VSS']=='EXECUTED'
    odb=source/'upgraded_parent_NOT_SYSTEM.odb';lib=source/'actual_child_timing.lib'
    for p in [odb,lib]:assert sha(p)==q['files'][p.name]['sha256']
    view=ROOT/'mxu_actual_tip_views/r01/mxu-C';vp=view/'execution.json';v=json.loads(vp.read_text())
    assert v.get('completed_utc') and v['source_geometry_sha256']==q['actual_new_leaf_ODB_SHA256'] and v['SPEF_replay_matches_source']
    assert sha(view/'timing.lib')==v['files']['timing.lib']['sha256']==q['new_source_research_model_SHA256']
    raw=(view/'timing.lib').read_text()
    expected,n=re.subn(r'(\bcell\s*\(\s*"?)llhd_opentpu_mxu("?\s*\))',lambda m:m[1]+'p126_mxu_actual_tip_r01'+m[2],raw)
    # Derive the source cell name from the actual model when its wrapper differs.
    if n!=1:
        names=re.findall(r'\bcell\s*\(\s*"?([^"\s\)]+)"?\s*\)',raw);assert len(names)==1
        expected,n=re.subn(r'(\bcell\s*\(\s*"?)'+re.escape(names[0])+r'("?\s*\))',lambda m:m[1]+'p126_mxu_actual_tip_r01'+m[2],raw)
    assert n==1 and expected==lib.read_text(),'Only actual source macro cell declaration may be aliased'
    trial=ROOT/'trials/access-r03/mxu-C/execution.json';old=json.loads(trial.read_text());sdc=Path(old['source_sdc'])
    assert sha(sdc)==old['input_sha256'][str(sdc)]
    inputs={str(p):sha(p) for p in [rp,odb,lib,vp,view/'timing.lib',trial,sdc]}
    out=ROOT/'mxu_actual_parent_rc_sta'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'CURRENT_ACTUAL_MXU_PARENT_EXTRACTED_RC_STA_EQUAL_RESEARCH_IO_POLICY_NOT_SYSTEM_QUALIFICATION',
         'full_qualification':False,'source_SHA':inputs,'source_leaf_ODB_SHA256':v['source_geometry_sha256'],
         'source_parent_native_DRC_count':0,'source_parent_all2172_nets_connected':True,
         'source_parent_zero_wire_direct_contact_nets':q['whole_parent_signal_geometry']['physically_touching_zero_wire_nets'],
         'native_output_load_values':[2,10,50],'native_capacitance_unit':'READ_NATIVE_REPORT_NOT_ASSUMED',
         'new_IO_policy':['original source SDC/clock unchanged','max I/O delay0.2T/min0.05T','BUF_X4 input drive','clock transition0.05 native time units','output loads2/10/50 native capacitance units'],
         'not_checked':['Full original historical parent constraints','Leaf full GDS/SRAM and minimum_period coverage','Full-system RTL/STA/DRC qualification'],
         'source_model_minimum_period_present':v.get('minimum_period_present'),
         'post_RCX_physical_ODB_saved_or_promoted':False,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID']}
    try:
        lines=['read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib',
               'read_liberty '+tcl(lib),'read_db '+tcl(odb),'read_sdc '+tcl(sdc),'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl',
               'puts BEGIN_ACTUAL_NATIVE_UNITS;report_units;puts END_ACTUAL_NATIVE_UNITS',
               'set clocks [all_clocks];if {[llength $clocks]!=1 || [llength [get_ports clk]]!=1} {error "Original clock interface contract mismatch"}',
               'set clk [lindex $clocks 0];set period [get_property $clk period]',
               'set f [open '+tcl(out/'native_original_clock_period.txt')+' w];puts $f $period;close $f',
               'set in {};set clock_ports [get_ports clk];foreach p [all_inputs] {if {[lsearch -exact $clock_ports $p]<0} {lappend in $p}}',
               'set_input_delay -clock $clk -max [expr {.2*$period}] $in','set_input_delay -clock $clk -min [expr {.05*$period}] $in',
               'set_output_delay -clock $clk -max [expr {.2*$period}] [all_outputs]','set_output_delay -clock $clk -min [expr {.05*$period}] [all_outputs]',
               'set_driving_cell -lib_cell BUF_X4 -pin Z $in','set_input_transition .05 [get_ports clk]',
               'write_sdc '+tcl(out/'research_interface.sdc'),
               'define_process_corner -ext_model_index 0 X','set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules',
               'extract_parasitics','write_spef '+tcl(out/'extracted.spef'),'read_spef '+tcl(out/'extracted.spef'),
               'report_wire_length -detailed_route -summary -file '+tcl(out/'wire_length.csv')]
        for load in [2,10,50]:
            prefix=str(out/('load'+str(load)))
            lines+=['set_load '+str(load)+' [all_outputs]',
              'report_worst_slack -max -digits 6 > '+tcl(prefix+'.setup.txt'),'report_worst_slack -min -digits 6 > '+tcl(prefix+'.hold.txt'),
              'report_tns -max -digits 6 > '+tcl(prefix+'.setup_tns.txt'),'report_tns -min -digits 6 > '+tcl(prefix+'.hold_tns.txt'),
              'report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > '+tcl(prefix+'.checks.txt'),
              'report_checks -path_delay min_max -group_path_count 12 -endpoint_path_count 1 -fields {capacitance slew fanout} -format full_clock_expanded -digits 6 > '+tcl(prefix+'.critical.txt'),
              'check_setup -verbose > '+tcl(prefix+'.constraint_coverage.txt'),'report_parasitic_annotation -report_unannotated > '+tcl(prefix+'.parasitic_coverage.txt')]
        script=out/'run.tcl';script.write_text('\n'.join(lines)+'\n')
        common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
                '--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
                '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
                '--home',str(ROOT/'home'),'--pwd',str(out)]
        rec['actual_OpenROAD_binary_SHA256']=subprocess.check_output(common+[IMAGE,'sha256sum',BIN]).decode().split()[0]
        rec['native_returncode']=execute(common,script,out/'native.log',threads=4)
        units=re.search(r'BEGIN_ACTUAL_NATIVE_UNITS\s*\n(.*?)END_ACTUAL_NATIVE_UNITS',(out/'native.log').read_text(),re.S)
        if units:
            rec['actual_native_units_text']=units[1];(out/'native_units.txt').write_text(units[1])
        if (out/'native_original_clock_period.txt').exists():rec['actual_original_clock_period_native_units']=(out/'native_original_clock_period.txt').read_text().strip()
        rec['observations']={}
        for load in [2,10,50]:
            row={}
            for kind in ['setup','hold']:
                p=out/('load'+str(load)+'.'+kind+'.txt');m=re.search(r'worst slack (?:max|min)\s+([-\d.]+)',p.read_text()) if p.exists() else None
                row[kind+'_ns']=float(m[1]) if m else None
            p=out/('load'+str(load)+'.checks.txt');row['literal_VIOLATED_markers_not_complete_failure_count']=p.read_text().count('(VIOLATED)') if p.exists() else None
            rec['observations'][str(load)]=row
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==s for p,s in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    passed=not rec.get('actual_failure') and rec.get('native_returncode')==0 and rec['all_closed_sources_unchanged']
    passed=passed and all(r.get('setup_ns') is not None and r['setup_ns']>=0 and r.get('hold_ns') is not None and r['hold_ns']>=0 and r['literal_VIOLATED_markers_not_complete_failure_count']==0 for r in rec.get('observations',{}).values())
    return 0 if passed else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
