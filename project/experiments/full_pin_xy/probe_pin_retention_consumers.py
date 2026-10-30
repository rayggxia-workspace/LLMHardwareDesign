"""Test exact old-pin WIRE retention through native and real export consumers."""
from pathlib import Path
import csv,datetime,json,os,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,BIN,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
DRIVER=Path(__file__).resolve().parent

def run(revision):
    source=ROOT/'upper_adaptation_trial/r02/opentpu/placed_adapter_NOT_SYSTEM.odb'
    prior=json.loads((source.parent/'execution.json').read_text());assert sha(source)==prior['files'][source.name]['sha256']
    out=ROOT/'pin_retention_consumers'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'SMALL_NATIVE_WIRE_REPRESENTATION_AND_EXPORT_CONSUMERS_NOT_ACTUAL_LEAF_REPAIR','source_SHA':{str(source):sha(source)},'scheduler_job':os.environ['SLURM_JOB_ID'],'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'full_qualification':False,'native_returncodes':{}}
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    try:
        # Identical point-pair and a nonzero centerline with explicit zero
        # extensions represent the exact same 280x280 DBU conductor square.
        body='''set b [ord::get_db_block];set layer [[ord::get_db_tech] findLayer metal5]
set f [open STATUS w];puts $f "method\\tfailed\\tmessage"
foreach method {POINT_PAIR NONZERO_ZEROEXT} {
 set n [odb::dbNet_create $b HPY_RETAIN_$method];set w [odb::dbWire_create $n]
 set enc [odb::dbWireEncoder];$enc begin $w;$enc newPath $layer ROUTED
 set failed [catch {
  if {$method eq "POINT_PAIR"} {$enc addPoint 200000 200000;$enc addPoint 200000 200000} else {$enc addPoint 239860 200000 0;$enc addPoint 240140 200000 0}
 } message];catch {$enc end}
 puts $f [join [list $method $failed [string map [list \\n { | } \\t { }] $message]] "\\t"]
};close $f
set ::env(PINXY_ACCESS_NET_NAMES) {HPY_RETAIN_POINT_PAIR HPY_RETAIN_NONZERO_ZEROEXT}
set ::env(PINXY_ACCESS_OUT) SHAPES
source EXPORTER
write_db ODBFILE
write_def DEFFILE
write_abstract_lef -bloat_factor 0 LEFFILE
'''
        for k,p in [('STATUS',out/'method_status.tsv'),('SHAPES',out/'native_shapes.tsv'),('EXPORTER',DRIVER/'export_access.tcl'),('ODBFILE',out/'probe_NOT_LEAF.odb'),('DEFFILE',out/'probe_NOT_LEAF.def'),('LEFFILE',out/'probe_detailed.lef')]:body=body.replace(k,tcl(p))
        s=out/'probe.tcl';s.write_text('read_db '+tcl(source)+'\n'+body);rec['native_returncodes']['native_create']=execute(common,s,out/'native.log',threads=1)
        assert rec['native_returncodes']['native_create']==0
        rows=list(csv.DictReader((out/'native_shapes.tsv').open(),delimiter='\t'));rec['native_shapes']=rows
        spec={'def':str(out/'probe_NOT_LEAF.def'),'output':str(out),'tech_lef':str(ROOT/'upper_layer_probe/r01/model/research12.tech.lef')};(out/'input.json').write_text(json.dumps(spec))
        cmd=common+[IMAGE,'klayout','-b','-r',str(DRIVER/'check_pin_retention_stream.py'),'-rd','spec='+str(out/'input.json')]
        with (out/'stream.log').open('w') as f:rec['native_returncodes']['KLayout_actual_DEF_read_GDS_roundtrip']=subprocess.call(cmd,stdout=f,stderr=subprocess.STDOUT)
        if (out/'stream.json').exists():rec['actual_stream_consumer']=json.loads((out/'stream.json').read_text())
        rec['original_source_unchanged']=sha(source)==rec['source_SHA'][str(source)]
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');return int(bool(rec.get('actual_failure')) or rec['native_returncodes'].get('KLayout_actual_DEF_read_GDS_roundtrip')!=0)
if __name__=='__main__':sys.exit(run(sys.argv[1]))
