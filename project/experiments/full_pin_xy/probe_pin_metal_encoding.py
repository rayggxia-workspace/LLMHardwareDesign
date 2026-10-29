"""Installed native square-metal encoding probe, never a real leaf repair."""
from pathlib import Path
import csv,datetime,json,os,sys,traceback,subprocess
from run_exports import ROOT,IMAGE,BIN,sha
from run_parent_trial import tcl
from run_escape_fixture import execute

DRIVER=Path(__file__).resolve().parent


def run(revision):
    source=ROOT/'upper_branch_neighbors/r01/llaccel';rp=source/'execution.json';q=json.loads(rp.read_text())
    odb=source/'routed_770_BRANCHES_NOT_SYSTEM.odb';assert q.get('completed_utc') and sha(odb)==q['files'][odb.name]['sha256']
    inputs={str(p):sha(p) for p in [rp,odb]};out=ROOT/'pin_metal_encoding_API'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'NATIVE_ENCODING_OF_EXACT_OLD_PIN_METAL_CAPABILITY_ONLY_NOT_REAL_LEAF_OR_DRC_REPAIR',
         'source_SHA':inputs,'full_qualification':False,'scheduler_job':os.environ['SLURM_JOB_ID'],
         'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'requested_layer':'metal5',
         'requested_square_DBU':[3975860,2411220,3976140,2411500],'native_returncodes':{}}
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    try:
        body='''set b [ord::get_db_block];set layer [[ord::get_db_tech] findLayer metal5]
if {[$b getDbUnitsPerMicron]!=2000 || [$layer getWidth]!=280} {error "Original native M5 dimensions differ"}
set f [open STATUS w];puts $f "method\tstatus\tmessage"
puts "ACTUAL_RECT_ENCODING_API [info commands ::odb::*WireEncoder*Rect*]"
foreach method {POINT_PAIR RECT_OPCODE} {
 set n [odb::dbNet_create $b HPY_PATCH_$method];set w [odb::dbWire_create $n];set enc [odb::dbWireEncoder];$enc begin $w
 $enc newPath $layer ROUTED;$enc addPoint 3976000 2411360
 set failed [catch {
  if {$method eq "POINT_PAIR"} {$enc addPoint 3976000 2411360} else {$enc addRect -140 -140 140 140}
  $enc end
 } message]
 puts $f [join [list $method $failed [string map [list \n { | } \t { }] $message]] "\t"]
};close $f
set ::env(PINXY_ACCESS_NET_NAMES) {HPY_PATCH_POINT_PAIR HPY_PATCH_RECT_OPCODE}
set ::env(PINXY_ACCESS_OUT) SHAPES
source EXPORTER
write_db NEWODB
write_def NEWDEF
'''
        for key,path in [('STATUS',out/'actual_encoding_status.tsv'),('SHAPES',out/'before_readback.tsv'),('EXPORTER',DRIVER/'export_access.tcl'),('NEWODB',out/'encoding_probe_NOT_LEAF.odb'),('NEWDEF',out/'encoding_probe_NOT_LEAF.def')]:body=body.replace(key,tcl(path))
        script=out/'encode.tcl';script.write_text('read_db '+tcl(odb)+'\n'+body)
        rec['actual_OpenROAD_binary_SHA256']=subprocess.check_output(common+[IMAGE,'sha256sum',BIN]).decode().split()[0]
        rec['native_returncodes']['encode_and_export']=execute(common,script,out/'native.log',threads=1)
        assert rec['native_returncodes']['encode_and_export']==0
        script=out/'readback.tcl';script.write_text('read_db '+tcl(out/'encoding_probe_NOT_LEAF.odb')+'\nset ::env(PINXY_ACCESS_NET_NAMES) {HPY_PATCH_POINT_PAIR HPY_PATCH_RECT_OPCODE}\nset ::env(PINXY_ACCESS_OUT) '+tcl(out/'after_readback.tsv')+'\nsource '+tcl(DRIVER/'export_access.tcl')+'\n')
        rec['native_returncodes']['independent_native_readback']=execute(common,script,out/'readback.log',threads=1)
        assert rec['native_returncodes']['independent_native_readback']==0
        assert (out/'before_readback.tsv').read_bytes()==(out/'after_readback.tsv').read_bytes()
        rec['actual_native_material_persisted_byteexact']=True
        rows=list(csv.DictReader((out/'after_readback.tsv').open(),delimiter='\t'))
        rec['encoding_results']={}
        for method in ['POINT_PAIR','RECT_OPCODE']:
            actual=[r for r in rows if r['net']=='HPY_PATCH_'+method]
            rec['encoding_results'][method]={'actual_rows':actual,'exact_requested_M5_square':len(actual)==1 and actual[0]['kind']=='WIRE' and actual[0]['layer']=='metal5' and [int(actual[0][k]) for k in ['x0','y0','x1','y1']]==rec['requested_square_DBU']}
        rec['not_checked']=['Actual signal/PG/OBS clearance','Native DRC on a real leaf','Exact GDS representation','RC/STA/parent accessibility']
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==s for p,s in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return 0 if not rec.get('actual_failure') and rec['all_closed_sources_unchanged'] else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
