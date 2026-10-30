"""Read-only installed antenna API/diode/real-route audit; never waive deck findings."""
from pathlib import Path
import datetime,json,os,subprocess,sys
from run_exports import ROOT,IMAGE,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from cell_semantics import groups

DRIVER=Path(__file__).resolve().parent


def run(revision):
    source=ROOT/'eco_views/r02/gemm-C';proof=json.loads((source/'execution.json').read_text());odb=source/'clean.odb'
    assert proof.get('completed_utc') and sha(odb)==proof['source_geometry_sha256']
    out=ROOT/'antenna_audit'/revision;out.mkdir(parents=True,exist_ok=False)
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    api=out/'help.tcl';api.write_text('\n'.join('help '+c for c in ['check_antennas','repair_antennas','estimate_parasitics','read_global_route_segments'])+'\n')
    rc=execute(common,api,out/'help.log',threads=1);assert rc==0
    help_text=(out/'help.log').read_text()
    script=out/'audit.tcl';script.write_text('\n'.join([
      'read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib',
      'read_db '+tcl(odb),'set b [ord::get_db_block];set f [open '+tcl(out/'diode_masters.tsv')+' w]',
      'puts $f "master\\ttype\\twidth_dbu\\theight_dbu\\tpins"',
      'foreach lib [[ord::get_db] getLibs] {foreach m [$lib getMasters] {if {[regexp -nocase {antenna|diode} [$m getName]]} {set pins {};foreach t [$m getMTerms] {lappend pins [list [$t getName] [$t getIoType] [$t getSigType]]};puts $f [join [list [$m getName] [$m getType] [$m getWidth] [$m getHeight] $pins] "\\t"]}}};close $f',
      'set f [open '+tcl(out/'installed_antenna_API.txt')+' w];foreach pattern {odb::dbTechLayer_*Antenna* odb::dbMTerm_*Antenna* est::*parasitic* ant::*} {puts $f [list $pattern [info commands $pattern]]};close $f',
      'check_antennas'+(' -report_file '+tcl(out/'native_antenna_report.txt') if '-report_file' in help_text else ''),
      'puts "READ_ONLY_NATIVE_ANTENNA_CHECK_EXECUTED_NOT_FULL_DECK_QUALIFICATION"'])+'\n')
    before=sha(odb);native=execute(common,script,out/'native.log',threads=4)
    lib='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
    text=subprocess.check_output(['singularity','exec','--cleanenv','--home',str(ROOT/'home'),IMAGE,'cat',lib]).decode()
    selected=[(name,body) for name,body in groups(text,'cell') if 'antenna' in name.lower() or 'diode' in name.lower()]
    (out/'actual_diode_liberty_blocks.txt').write_text('\n'.join('cell ('+name+') {\n'+body+'\n}' for name,body in selected)+'\n')
    rec={'scope':'READ_ONLY_ANTENNA_API_AND_EXISTING_ROUTE_AUDIT_NOT_REPAIR_OR_FULL_QUALIFICATION',
      'source_ODB':str(odb),'source_ODB_SHA':before,'source_unchanged':sha(odb)==before,
      'source_view_receipt_SHA':sha(source/'execution.json'),'native_returncode':native,'API_help_returncode':rc,
      'native_report_option_supported':'-report_file' in help_text,'actual_diode_liberty_cells':[n for n,b in selected],
      'full_qualification':False,'not_claimed':['KLayout1460 antenna findings repaired','new diode capacitance characterized','whole-design STA','full manufacture rules'],
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
      'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');print('ANTENNA_AUDIT',native,'NOT_QUALIFIED',flush=True)
    return native


if __name__=='__main__':sys.exit(run(sys.argv[1]))
