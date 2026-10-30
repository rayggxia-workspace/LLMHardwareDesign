"""Read installed RAM-generator capability; never fabricate missing SRAM GDS.

Official API reference: OpenROAD src/ram/README.md. Capability presence is not
generated memory, pin/model equivalence, physical closure or a legal replacement.
"""
from pathlib import Path
import datetime,json,os,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,BIN,sha
from run_escape_fixture import execute
from run_parent_trial import tcl

DRIVER=Path(__file__).resolve().parent


def run(revision):
    out=ROOT/'native_ram_capability'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'INSTALLED_NATIVE_RAM_API_PROBE_NOT_MEMORY_IMPLEMENTATION_OR_REPLACEMENT',
      'full_qualification':False,'generated_memory':False,'existing_leaf_or_fake_memory_modified':False,
      'reference':'https://openroad.readthedocs.io/en/latest/main/src/ram/README.html',
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID']}
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    try:
        rec['actual_OpenROAD_binary_SHA256']=subprocess.check_output(common+[IMAGE,'sha256sum',BIN]).decode().split()[0]
        lib='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
        rec['actual_Liberty_SHA256']=subprocess.check_output(common+[IMAGE,'sha256sum',lib]).decode().split()[0]
        code='''read_liberty '''+tcl(lib)+'''
set f [open '''+tcl(out/'capability.tsv')+''' w]
puts $f "item\\tvalue"
puts $f "generate_ram_present\\t[expr {[llength [info commands generate_ram]]==1}]"
puts $f "ram_namespace_commands\\t[info commands ram::*]"
close $f
if {[llength [info commands generate_ram]]} {
 help generate_ram
 set f [open '''+tcl(out/'generate_ram.body.tcl')+''' w]
 if {[catch {info body generate_ram} body]} {puts $f NATIVE_COMPILED_ENTRY_NO_TCL_BODY} else {puts -nonewline $f $body}
 close $f
}
'''
        script=out/'probe.tcl';script.write_text(code)
        rec['native_probe_returncode']=execute(common,script,out/'native.log',threads=1)
        if (out/'capability.tsv').exists():
            lines=(out/'capability.tsv').read_text().splitlines()
            rec['generate_ram_present']='generate_ram_present\t1' in lines
        rec['interpretation']='Capability only. A real generator must preserve 1r1w/per-bit mask/read latency/collision semantics, capacity, actual dimensions and pin/layer contracts before any new costed variant can replace a synthetic fakeram.'
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return 0 if rec.get('native_probe_returncode')==0 else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
