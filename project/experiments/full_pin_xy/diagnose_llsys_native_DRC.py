"""Read exact three-net/four-marker LL SYSTEM geometry and local fixed PG.

Reuse its closed whole-net native export, rather than rerouting an experiment.
No source wire, pin, PG, rule, SDC or active full-window driver is changed.
"""
from pathlib import Path
import csv,datetime,gzip,json,os,re,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from check_access import check

DRIVER=Path(__file__).resolve().parent


def run(revision):
    source=ROOT/'finalized/llsys-pg-r03/llaccel_aux-C';rp=source/'execution.json';prior=json.loads(rp.read_text())
    assert prior['export_returncode']==prior['independent_DRC_returncode']==0 and prior['independent_DRC_count']==4
    assert prior['whole_access']['pass'] and prior['whole_access']['checked_nets']==725253
    odb=source/'clean.odb';whole=source/'whole_access.tsv.gz';drc=source/'independent.drc'
    for p in [odb,whole,drc]:assert sha(p)==prior['files'][p.name]['sha256']
    assert sha(odb)==prior['clean_odb_sha256']==prior['source_sha256']
    markers=[]
    for entry in drc.read_text().split('violation type:')[1:]:
        names=re.findall(r'net:([^\s]+)',entry);m=re.search(r'bbox = \(([^,]+), ([^)]+)\) - \(([^,]+), ([^)]+)\) on Layer (\w+)',entry);assert m
        box=list(map(float,m.groups()[:4]));window=[round((box[0]-2)*2000),round((box[1]-2)*2000),round((box[2]+2)*2000),round((box[3]+2)*2000)]
        markers.append({'type':entry.splitlines()[0].strip(),'nets':names,'layer':m[5],'actual_bbox_um':box,'diagnostic_window_DBU':window})
    targets=sorted({n for m in markers for n in m['nets'] if n not in ['VDD','VSS']})
    assert len(markers)==4 and targets==['bit_1382013','bit_1389626','bit_6907']
    out=ROOT/'llsys_DRC_diagnosis'/revision;out.mkdir(parents=True,exist_ok=False)
    inputs={str(p):sha(p) for p in [rp,odb,whole,drc]}
    rec={'scope':'THREE_ACTUAL_NETS_ALL_FOUR_NATIVE_MARKERS_LOCAL_FOREIGN_METAL_AND_FIXED_PG_NOT_REPAIR_OR_DRC_PASS',
      'source_SHA':inputs,'source_native_DRC_count':4,'source_all_multiterminal_nets':725253,
      'markers':markers,'all_three_actual_target_nets':targets,'DBU_per_um':2000,
      'source_kind':'Complete PG-only internal C alternative; does not replace active full-window 92690/92691',
      'full_qualification':False,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
      'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    def save():(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    save()
    try:
        # Actual native whole export is closed and SHA-bound. Scan once, retain
        # every target-net shape plus every other-net shape touching the ROIs.
        with gzip.open(whole,'rt') as f,(out/'three_complete_actual_nets.tsv').open('w',newline='') as tf,(out/'local_actual_other_signal_clock.tsv').open('w',newline='') as rf:
            reader=csv.DictReader(f,delimiter='\t');columns=reader.fieldnames
            tw=csv.DictWriter(tf,fieldnames=columns,delimiter='\t',lineterminator='\n');tw.writeheader()
            rw=csv.DictWriter(rf,fieldnames=columns+['marker_ids'],delimiter='\t',lineterminator='\n');rw.writeheader()
            scanned=selected=local=0
            for row in reader:
                scanned+=1
                if row['net'] in targets:tw.writerow(row);selected+=1
                if row['kind']=='UNROUTED':continue
                b=[int(row[k]) for k in ['x0','y0','x1','y1']]
                hits=[i for i,m in enumerate(markers) if b[0]<=m['diagnostic_window_DBU'][2] and b[2]>=m['diagnostic_window_DBU'][0] and b[1]<=m['diagnostic_window_DBU'][3] and b[3]>=m['diagnostic_window_DBU'][1]]
                if hits:rw.writerow(dict(row,marker_ids=','.join(map(str,hits))));local+=1
        rec['whole_export_rows_scanned']=scanned;rec['all_target_rows']=selected;rec['local_signal_clock_rows']=local
        rec['all_three_net_connectivity_replay']=check(out/'three_complete_actual_nets.tsv',True)
        assert rec['all_three_net_connectivity_replay']['pass'] and rec['all_three_net_connectivity_replay']['checked_nets']==3
        save()
        common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
        code='''set b [ord::get_db_block];if {[$b getDbUnitsPerMicron]!=2000} {error "DBU mismatch"}
set windows '''+('[list '+' '.join(tcl(' '.join(map(str,m['diagnostic_window_DBU']))) for m in markers)+']')+'''
set f [open '''+tcl(out/'actual_PG_and_OBS_local.tsv')+''' w];puts $f "net\\tlayer\\tx0\\ty0\\tx1\\ty1\\tkind\\towner\\tmarker_ids"
proc local_box {nn layer x0 y0 x1 y1 kind owner} {
 global f windows;set hits {};set index 0
 foreach w $windows {lassign $w a c d e;if {$x0<=$d && $x1>=$a && $y0<=$e && $y1>=$c} {lappend hits $index};incr index}
 if {[llength $hits]} {puts $f [join [list $nn $layer $x0 $y0 $x1 $y1 $kind $owner [join $hits ,]] "\\t"]}
}
proc local_shape {nn r kind owner {dx 0} {dy 0}} {local_box $nn [[$r getTechLayer] getName] [expr {[$r xMin]+$dx}] [expr {[$r yMin]+$dy}] [expr {[$r xMax]+$dx}] [expr {[$r yMax]+$dy}] $kind $owner}
foreach name {VDD VSS} {
 set n [$b findNet $name];if {$n eq "NULL"} {error "Original fixed PG missing"}
 foreach sw [$n getSWires] {foreach s [$sw getWires] {
  if {[$s isVia]} {set v [$s getTechVia];if {$v eq "NULL"} {set v [$s getBlockVia]};lassign [$s getViaXY] x y;foreach r [$v getBoxes] {local_shape $name $r PG_VIA {} $x $y}} else {local_shape $name $s PG_WIRE {}}
 }}
}
foreach ob [$b getObstructions] {local_shape UNOWNED_BLOCK_OBS [$ob getBBox] BLOCK_OBS {}}
foreach i [$b getInsts] {
 set m [$i getMaster];if {[$m getType] ne "BLOCK"} {continue}
 set bb [$i getBBox];set relevant 0
 foreach w $windows {lassign $w a c d e;if {[$bb xMin]<=$d && [$bb xMax]>=$a && [$bb yMin]<=$e && [$bb yMax]>=$c} {set relevant 1}}
 if {!$relevant} {continue};lassign [$m getOrigin] ox oy
 if {[$i getOrient] eq "R0" && $ox==0 && $oy==0} {lassign [$i getLocation] x y;foreach ob [$m getObstructions] {local_shape UNOWNED_MACRO_OBS $ob MACRO_OBS [$i getName] $x $y}} else {local_box UNKNOWN_TRANSFORM UNKNOWN [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax] UNCHECKED_MACRO_TRANSFORM [$i getName]}
};close $f
set f [open '''+tcl(out/'actual_layer_rules.tsv')+''' w];puts $f "layer\\twidth_DBU\\tspacing_DBU\\tpitch_x_DBU\\tpitch_y_DBU"
foreach ly [[ord::get_db_tech] getLayers] {puts $f [join [list [$ly getName] [$ly getWidth] [$ly getSpacing] [$ly getPitchX] [$ly getPitchY]] "\\t"]};close $f
puts {ACTUAL_LOCAL_FIXED_PG_AND_OBS_READ_ONLY_EXPORTED_NOT_RULE_PASS}
'''
        script=out/'local_fixed.tcl';script.write_text('read_db '+tcl(odb)+'\n'+code)
        rec['native_local_PG_OBS_export_returncode']=execute(common,script,out/'native.log',threads=1)
        rec['not_checked']=['Fresh native DRC or repair','PRL/EOL/via/enclosure or full rules','RC/STA/electrical or full function','One-terminal unused-net metal omitted by original whole-multiterminal export','Library internal GDS metal beyond native LEF/ODB view','Non-R0 macro OBS transforms marked UNKNOWN explicitly']
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==v for p,v in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    return 0 if 'actual_failure' not in rec and rec.get('native_local_PG_OBS_export_returncode')==0 and rec['all_closed_sources_unchanged'] else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
