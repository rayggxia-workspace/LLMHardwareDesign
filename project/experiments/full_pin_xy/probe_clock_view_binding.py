"""Small native source-bound clock binding diagnosis, not system qualification."""
from pathlib import Path
import datetime,json,os,re,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute

DRIVER=Path(__file__).resolve().parent


def run(revision):
    view=ROOT/'pin_escape_views/r01/mxu-C';vp=view/'execution.json';v=json.loads(vp.read_text())
    assert v['native_export_returncode']==0 and v['matching_all_signal_model_pins']==2172
    for n in ['abstract.lef','timing.lib']:assert sha(view/n)==v['files'][n]['sha256']
    src=ROOT/'trials/access-r03/mxu-C/execution.json';q=json.loads(src.read_text());sdc=Path(q['source_sdc'])
    assert sha(sdc)==q['input_sha256'][str(sdc)]
    clock_lines=[s for s in sdc.read_text().splitlines() if re.fullmatch(r'create_clock -name clk -period [0-9.]+ \[get_ports \{clk\}\]',s)]
    assert len(clock_lines)==1
    masters=re.findall(r'(?m)^MACRO (\S+)',(view/'abstract.lef').read_text());assert len(masters)==1
    master=masters[0];assert re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',master)
    out=ROOT/'clock_view_binding_probe'/revision;out.mkdir(parents=True,exist_ok=False)
    inputs={str(p):sha(p) for p in [vp,view/'abstract.lef',view/'timing.lib',src,sdc]}
    rec={'scope':'SMALL_NATIVE_CLOCK_TYPE_BINDING_API_PROBE_NOT_ACTUAL_PARENT_REPAIR',
         'source_SHA':inputs,'source_clock_statement':clock_lines[0],
         'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
         'full_qualification':False,'original_actual_parent_and_leaf_files_modified':False}
    try:
        verilog=out/'fixture.v';verilog.write_text('module mxu_clock_probe(input clk); '+master+' u_macro(.clk(clk)); endmodule\n')
        lines=['read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef',
          'read_lef '+tcl(view/'abstract.lef'),
          'set f [open '+tcl(out/'native_clock_types.tsv')+' w];puts $f "stage\tMTerm_USE\tITerm_USE\tnet_USE"',
          'proc clock_type {label} {global f;set m [[ord::get_db] findMaster '+tcl(master)+'];set mt [$m findMTerm clk];set it NULL;set ns NULL;set b [ord::get_db_block];if {$b ne "NULL"} {set i [$b findInst u_macro];if {$i ne "NULL"} {set t [$i findITerm clk];set it [$t getSigType];set n [$t getNet];if {$n ne "NULL"} {set ns [$n getSigType]}}};puts $f [join [list $label [$mt getSigType] $it $ns] "\t"]}',
          'clock_type after_LEF','read_liberty '+tcl(view/'timing.lib'),'clock_type after_Liberty',
          'read_verilog '+tcl(verilog),'link_design mxu_clock_probe','clock_type after_link_design',
          clock_lines[0],'clock_type after_original_create_clock','close $f']
        script=out/'probe.tcl';script.write_text('\n'.join(lines)+'\n')
        common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
        rec['native_probe_returncode']=execute(common,script,out/'native.log',threads=1)
        if (out/'native_clock_types.tsv').exists():rec['actual_native_stage_rows']=(out/'native_clock_types.tsv').read_text().splitlines()
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==h for p,h in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return 0 if 'actual_failure' not in rec and rec.get('native_probe_returncode')==0 and rec['all_closed_sources_unchanged'] else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
