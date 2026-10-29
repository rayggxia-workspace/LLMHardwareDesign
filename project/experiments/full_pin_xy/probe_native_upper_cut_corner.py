"""Native positive/negative control for actual via11 diagonal cut spacing."""
from pathlib import Path
import datetime,json,os,re,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
DRIVER=Path(__file__).resolve().parent
def run(revision):
    tech=ROOT/'upper_layer_probe/r01/model/research12.tech.lef';out=ROOT/'upper_cut_corner_probe'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'TINY_INDEPENDENT_NATIVE_RESEARCH_TECH_RULE_CONTROLS_NOT_SYSTEM_REPAIR','source_SHA':{str(tech):sha(tech)},'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],'full_qualification':False,'cases':{}}
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    try:
        (out/'fixture.v').write_text('module hpy_cut_fixture (inout a,b); endmodule\n')
        for name,yy in [('orthogonal_gap_0p8_EXPECT_FAIL',20.0),('diagonal_gap_0p8_0p8_NATIVE_DECIDES',21.6)]:
            sub=out/name;sub.mkdir()
            lines=['read_lef '+tcl(tech),'read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef','read_verilog '+tcl(out/'fixture.v'),'link_design hpy_cut_fixture','initialize_floorplan -die_area {0 0 50 50} -core_area {1 1 49 49} -site FreePDK45_38x28_10R_NP_162NW_34O','make_tracks','set b [ord::get_db_block];set tech [ord::get_db_tech]','if {[$b getDbUnitsPerMicron]!=2000} {error "Fixture unit mismatch"}']
            for pin,x,y in [('a',20.,20.),('b',21.6,yy)]:
                lines+=['place_pin -pin_name '+pin+' -layer metal11 -location {'+str(x)+' '+str(y)+'} -pin_size {.8 .8}',
                    'set n [[$b findBTerm '+pin+'] getNet];set w [odb::dbWire_create $n];set e [odb::dbWireEncoder];$e begin $w;$e newPath [$tech findLayer metal11] ROUTED;$e addPoint '+str(round(x*2000))+' '+str(round(y*2000))+';$e addTechVia [$tech findVia via11_0];$e end']
            lines+=['write_db '+tcl(sub/'fixture_NOT_SYSTEM.odb'),'write_def '+tcl(sub/'fixture.def'),'set_routing_layers -signal metal11-metal12 -clock metal11-metal12','drt::check_drc -output_file '+tcl(sub/'independent.drc')]
            script=sub/'probe.tcl';script.write_text('\n'.join(lines)+'\n');rc=execute(common,script,sub/'native.log',threads=1)
            text=(sub/'independent.drc').read_text() if (sub/'independent.drc').exists() else ''
            rec['cases'][name]={'native_returncode':rc,'native_DRC_count':len(re.findall(r'^violation type:',text,re.M)),'actual_native_findings':text}
        a=rec['cases']['orthogonal_gap_0p8_EXPECT_FAIL'];b=rec['cases']['diagonal_gap_0p8_0p8_NATIVE_DECIDES'];rec['native_controls_prove_corner_square_test_was_overconservative']=a['native_returncode']==b['native_returncode']==0 and a['native_DRC_count']>0 and b['native_DRC_count']==0
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_sources_unchanged']=all(sha(Path(p))==s for p,s in rec['source_SHA'].items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={str(p.relative_to(out)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.rglob('*') if p.is_file()};(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');return int(bool(rec.get('actual_failure')) or not rec.get('native_controls_prove_corner_square_test_was_overconservative'))
if __name__=='__main__':sys.exit(run(sys.argv[1]))
