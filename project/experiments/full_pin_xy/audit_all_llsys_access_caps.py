"""Inventory actual own-via candidates for every current LL signal pin.

Read-only. A same-net landing and track match do not prove an accessible pin.
No abstract obstacle is removed, and no source pin, wire or via is changed.
"""
from pathlib import Path
from collections import Counter
import csv,datetime,json,os,re,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute

DRIVER=Path(__file__).resolve().parent


def run(revision):
    source=ROOT/'llsys_parent_tip_views/r01/llaccel_aux-C'
    rp=source/'execution.json';q=json.loads(rp.read_text())
    assert q.get('completed_utc') and q['source_native_DRC']==0 and q['all_sources_and_pre_RCX_geometry_unchanged']
    odb=source/'clean.odb';pinfile=source/'pins.tsv';deffile=source/'clean.def'
    for p in [odb,pinfile,deffile]:assert sha(p)==q['files'][p.name]['sha256']
    tracks={}
    with deffile.open() as f:
        for line in f:
            m=re.match(r'TRACKS ([XY]) (\d+) DO (\d+) STEP (\d+) LAYER (metal[56]) ;',line)
            if m:tracks[m.group(5),m.group(1)]=(int(m.group(2)),int(m.group(4)))
            if line.startswith('COMPONENTS'):break
    assert len(tracks)==4
    pins=[r for r in csv.DictReader(pinfile.open(),delimiter='\t') if r['use'] not in ['POWER','GROUND']]
    assert len(pins)==13507 and len({r['pin'] for r in pins})==13507
    inputs={str(p):sha(p) for p in [rp,odb,pinfile,deffile]}
    out=ROOT/'all_llsys_actual_access_caps'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'ALL13507_CURRENT_NATIVE_OWN_VIA_TRACK_CANDIDATE_AUDIT_NOT_PIN_REPAIR_OR_PHYSICAL_ACCESS_PASS',
         'source_SHA':inputs,'source_geometry_SHA256':q['source_geometry_sha256'],
         'source_native_DRC_count':0,'source_pin_count':13507,
         'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
         'full_qualification':False,'maximum_candidate_L1_distance_um':5.0,
         'original_M5_M6_pin_size_DBU':280,'all_existing_geometry_unchanged':True,
         'not_checked':['Foreign signal/PG/OBS or transformed macro clearance at each candidate','Full per-layer cut/enclosure/spacing/DRC','Parent native AP and routing','RC/STA or functional qualification'],
         'duplicate_candidate_locations_are_risks_not_assigned_coordinates':True}
    try:
        tr=out/'native_tracks.tcl'
        tr.write_text('set tracks [dict create '+ ' '.join(tcl(layer+axis)+' '+tcl(' '.join(map(str,v))) for (layer,axis),v in sorted(tracks.items()))+']\n')
        body=r'''
set b [ord::get_db_block]
set f [open OUTPUT w]
puts $f "pin\tnet\tlayer\tx0\ty0\tx1\ty1\taligned_preferred\tcandidate_x\tcandidate_y\tdistance_DBU\tvia\tcap_x0\tcap_y0\tcap_x1\tcap_y1\tstatus"
set itr [odb::dbWirePathItr];set path [odb::dbWirePath];set ps [odb::dbWirePathShape]
foreach bt [$b getBTerms] {
 if {[$bt getSigType] in {POWER GROUND}} {continue}
 set boxes {};foreach p [$bt getBPins] {foreach box [$p getBoxes] {lappend boxes $box}}
 if {[llength $boxes]!=1} {error "Current original signal pin is not exactly one rectangle"}
 set box [lindex $boxes 0];set layer [[$box getTechLayer] getName]
 if {$layer ni {metal5 metal6} || [$box xMax]-[$box xMin]!=280 || [$box yMax]-[$box yMin]!=280} {error "Original layer/size mismatch"}
 set x [expr {([$box xMin]+[$box xMax])/2}];set y [expr {([$box yMin]+[$box yMax])/2}]
 set axis [expr {$layer eq "metal5" ? "Y" : "X"}];set coord [expr {$axis eq "Y" ? $y : $x}]
 lassign [dict get $tracks ${layer}${axis}] offset pitch
 set aligned [expr {($coord-$offset)%$pitch==0}]
 set n [$bt getNet];set best {};set bd 10001
 if {!$aligned && [$n getWire] ne "NULL"} {
  $itr begin [$n getWire]
  while {[$itr getNextPath $path]} {while {[$itr getNextShape $ps]} {
   set s [odb::dbWirePathShape_shape_get $ps];if {![$s isVia]} {continue}
   set via [$s getTechVia];if {$via eq "NULL"} {set via [$s getVia]}
   lassign [$s getViaXY] vx vy;set distance [expr {abs($vx-$x)+abs($vy-$y)}]
   if {$distance>10000 || $distance>=$bd} {continue}
   lassign [dict get $tracks metal6X] xo xp;lassign [dict get $tracks metal5Y] yo yp
   if {($vx-$xo)%$xp!=0 || ($vy-$yo)%$yp!=0} {continue}
   foreach cap [$via getBoxes] {
    if {[[$cap getTechLayer] getName] ne $layer} {continue}
    if {[$cap xMin]>-140 || [$cap yMin]>-140 || [$cap xMax]<140 || [$cap yMax]<140} {continue}
    set bd $distance;set best [list $vx $vy $distance [$via getName] [expr {$vx+[$cap xMin]}] [expr {$vy+[$cap yMin]}] [expr {$vx+[$cap xMax]}] [expr {$vy+[$cap yMax]}]]
   }
  }}
 }
 if {$aligned} {set status KEEP_ALREADY_TRACK_CENTERED} elseif {[llength $best]} {set status ACTUAL_OWN_VIA_GEOMETRIC_CANDIDATE_NOT_AP_VALIDATED} else {set status KEEP_NO_BOUNDED_OWN_VIA_FOUND}
 if {![llength $best]} {set best [list {} {} {} {} {} {} {} {}]}
 puts $f [join [concat [list [$bt getName] [$n getName] $layer [$box xMin] [$box yMin] [$box xMax] [$box yMax] $aligned] $best [list $status]] "\t"]
}
close $f
puts ALL13507_NATIVE_OWN_VIA_INVENTORY_READ_ONLY_NOT_REPAIR
'''
        script=out/'read_all_caps.tcl'
        script.write_text('read_db '+tcl(odb)+'\nsource '+tcl(tr)+'\n'+body.replace('OUTPUT',tcl(out/'all13507_actual_own_via_candidates.tsv')))
        common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
        rec['native_read_only_returncode']=execute(common,script,out/'native.log',threads=1)
        assert rec['native_read_only_returncode']==0
        rows=list(csv.DictReader((out/'all13507_actual_own_via_candidates.tsv').open(),delimiter='\t'))
        original={r['pin']:r for r in pins}
        assert len(rows)==len(original)==13507 and {r['pin'] for r in rows}==set(original)
        for r in rows:
            assert all(r[k]==original[r['pin']][k] for k in ['pin','net','layer','x0','y0','x1','y1'])
        rec['all_13507_original_pin_rectangles_nets_layers_exact']=True
        rec['status_counts']=dict(Counter(r['status'] for r in rows))
        selected=[r for r in rows if r['candidate_x']]
        points=Counter((r['layer'],r['candidate_x'],r['candidate_y']) for r in selected)
        rec['duplicate_candidate_point_groups']=sum(n>1 for n in points.values())
        rec['duplicate_candidate_pins']=sum(n for n in points.values() if n>1)
        rec['actual_error_bit1073']=next(r for r in rows if r['pin']=='bit_1073')
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==s for p,s in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return 0 if 'actual_failure' not in rec and rec['all_closed_sources_unchanged'] else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
