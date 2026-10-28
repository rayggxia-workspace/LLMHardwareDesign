"""Probe actual fixed dbWire encoding and two access rectangles before six-block use."""
from pathlib import Path
import datetime,json,os,sys
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute

DRIVER=Path(__file__).resolve().parent


def run(revision):
    out=ROOT/'fixed_wire_api'/revision;out.mkdir(parents=True,exist_ok=False)
    (out/'probe.v').write_text('module fixed_probe(input a); endmodule\n')
    tech=ROOT/'upper_layer_probe/r01/model/research12.tech.lef'
    script=out/'probe.tcl';script.write_text('\n'.join([
      'read_lef '+tcl(tech),'read_verilog '+tcl(out/'probe.v'),'link_design fixed_probe',
      'initialize_floorplan -die_area {0 0 100 100} -core_area {0 0 100 100} -site FreePDK45_38x28_10R_NP_162NW_34O','make_tracks',
      'place_pin -pin_name a -layer metal10 -location {19.295 19.27} -pin_size {.8 .8}',
      'set b [ord::get_db_block];set bt [$b findBTerm a];set net [$bt getNet];set ly [[ord::get_db_tech] findLayer metal10]',
      'set w [odb::dbWire_create $net];set enc [odb::dbWireEncoder];$enc begin $w;$enc newPath $ly FIXED;$enc addPoint 38590 38540;$enc addPoint 38590 102540;$enc end',
      'set bp [odb::dbBPin_create $bt];$bp setPlacementStatus FIXED;odb::dbBox_create $bp $ly 37790 101740 39390 103340',
      'write_db '+tcl(out/'fixed.odb'),'write_def '+tcl(out/'fixed.def'),
      'puts "ACTUAL_FIXED_DBWIRE_AND_TWO_BPIN_RECTS_CREATED"'])+'\n')
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    rc=execute(common,script,out/'native.log',threads=1)
    rec={'scope':'NATIVE_FIXED_WIRE_API_PROBE_ONLY_NOT_SYSTEM_OR_RULE_PASS','native_returncode':rc,
      'full_qualification':False,'technology_SHA':sha(tech),'scheduler_job':os.environ['SLURM_JOB_ID'],
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
      'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    if rc==0:
        text=(out/'fixed.def').read_text();rec['DEF_has_FIXED_M10_wire']=' + FIXED metal10' in text or '+ FIXED metal10' in text
        rec['DEF_fixed_wire_excerpt']='\n'.join(s for s in text.splitlines() if 'FIXED' in s or 'metal10' in s)
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');print('FIXED_WIRE_API',rc,flush=True);return rc


if __name__=='__main__':sys.exit(run(sys.argv[1]))
