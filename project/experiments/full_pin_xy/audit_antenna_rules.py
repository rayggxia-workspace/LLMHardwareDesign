"""Read actual installed rule sources and native rule presence, without modifying routes."""
from pathlib import Path
import datetime,json,os,re,subprocess,sys
from run_exports import ROOT,IMAGE,sha
from run_parent_trial import tcl
from run_escape_fixture import execute

DRIVER=Path(__file__).resolve().parent


def run(revision):
    source=ROOT/'eco_views/r02/gemm-C/clean.odb'
    out=ROOT/'antenna_rules'/revision;out.mkdir(parents=True,exist_ok=False)
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    platform='/OpenROAD-flow-scripts/flow/platforms/nangate45'
    paths=[platform+'/lef/NangateOpenCellLibrary.tech.lef',platform+'/lef/NangateOpenCellLibrary.macro.mod.lef',
           platform+'/drc/FreePDK45.lydrc',platform+'/lib/NangateOpenCellLibrary_typical.lib']
    inputs={};contexts=[]
    for path in paths:
        raw=subprocess.check_output(common+[IMAGE,'cat',path]);dest=out/Path(path).name;dest.write_bytes(raw)
        text=raw.decode();lines=text.splitlines();selected=set()
        for i,line in enumerate(lines):
            if re.search(r'antenna|diode|capacitive_load_unit',line,re.I):selected.update(range(max(0,i-3),min(len(lines),i+5)))
        contexts.append('\nSOURCE '+path+'\n'+'\n'.join(str(i+1)+': '+lines[i] for i in sorted(selected)))
        inputs[path]={'sha256':sha(dest),'bytes':len(raw),'antenna_keyword_count':len(re.findall('antenna',text,re.I))}
    (out/'rule_contexts.txt').write_text('\n'.join(contexts)+'\n')
    script=out/'audit.tcl';script.write_text('\n'.join([
      'read_liberty '+tcl(paths[-1]),'read_db '+tcl(source),
      'set f [open '+tcl(out/'layer_rule_presence.tsv')+' w];puts $f "layer\\trouting_level\\thas_default_antenna_rule\\thas_oxide2_rule"',
      'foreach ly [[ord::get_db_tech] getLayers] {if {[$ly getRoutingLevel]>0} {puts $f [join [list [$ly getName] [$ly getRoutingLevel] [$ly hasDefaultAntennaRule] [$ly hasOxide2AntennaRule]] "\\t"]}};close $f',
      'set f [open '+tcl(out/'installed_rule_methods.txt')+' w];foreach pattern {odb::dbTechLayerAntennaRule_* odb::dbMTerm_*Ant* odb::dbAntenna*} {puts $f [list $pattern [lsort [info commands $pattern]]]};close $f',
      'check_antennas -verbose -report_file '+tcl(out/'native_verbose_report.txt'),
      'puts "ANTENNA_RULE_PRESENCE_AUDIT_NOT_REPAIR"'])+'\n')
    before=sha(source);rc=execute(common,script,out/'native.log',threads=4)
    rec={'scope':'READ_ONLY_INSTALLED_ANTENNA_RULE_AND_MODEL_AUDIT_NOT_REPAIR',
      'source_ODB':str(source),'source_ODB_SHA':before,'source_unchanged':sha(source)==before,
      'installed_source_files':inputs,'native_returncode':rc,'full_qualification':False,
      'GDS1460_not_repaired':True,'scheduler_job':os.environ['SLURM_JOB_ID'],
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
      'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');return rc


if __name__=='__main__':sys.exit(run(sys.argv[1]))
