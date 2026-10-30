"""Resolve every unannotated driver against the actual repaired LL database.

Do not call dangling/unconnected outputs extraction failures; do not waive a
multi-terminal missing RC model merely because RCX returned zero.
"""
from pathlib import Path
from collections import Counter
import csv,datetime,json,os,re,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
DRIVER=Path(__file__).resolve().parent


def run(revision):
    source=ROOT/'llsys_corner_fill/r01';rp=source/'execution.json';q=json.loads(rp.read_text())
    assert q.get('completed_utc') and not q.get('actual_failure') and q['native_returncodes']['RC_STA']==0
    paths=[source/'routed.odb',source/'parasitic_coverage.txt']
    for p in paths:assert sha(p)==q['files'][p.name]['sha256']
    lines=paths[1].read_text().splitlines();count=int(re.fullmatch(r'Found (\d+) unannotated drivers\.',lines[0])[1])
    stop=next(i for i,s in enumerate(lines[1:],1) if s.startswith('Found '));names=[s.strip() for s in lines[1:stop] if s.strip()]
    assert len(names)==count
    norm=lambda s:re.sub(r'\\([\[\]])',r'\1',s)
    assert len({norm(n) for n in names})==count,'Ambiguous actual STA display names'
    out=ROOT/'llsys_corner_unannotated'/revision;out.mkdir(parents=True,exist_ok=False)
    inputs={str(p):sha(p) for p in paths+[rp]}
    r={'scope':'ALL_REPORTED_UNANNOTATED_DRIVERS_ACTUAL_NATIVE_NET_INVENTORY_NOT_RC_WAIVER_OR_SIGNOFF',
       'source_SHA':inputs,'reported_unannotated_drivers':count,'source_ODB_SHA256':sha(paths[0]),
       'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
       'full_qualification':False,'actual_physical_or_constraint_modification':False}
    try:
        spec='set wanted [dict create]\n'+''.join('dict set wanted '+tcl(norm(n))+' '+tcl(n)+'\n' for n in names)
        body=spec+'\nread_db '+tcl(paths[0])+'\nset output [open '+tcl(out/'all_reported_drivers.tsv')+' w]\n'+r'''
puts $output "reported_driver\tkind\tinstance\tpin\tnative_net\tnative_sigtype\tITerms\tBTerms\tnative_WIRE\tclassification"
set seen [dict create]
proc observe_driver {display kind inst pin net} {
 global wanted seen output
 set key [regsub -all {\\([\[\]])} $display {\1}]
 if {![dict exists $wanted $key]} {return}
 if {[dict exists $seen $key]} {error "Ambiguous actual native driver: $key"}
 dict set seen $key 1
 set nn NULL;set sig NONE;set ni 0;set nb 0;set wire 0
 if {$net eq "NULL"} {set cls UNCONNECTED_NATIVE_TERMINAL} else {
  set nn [$net getName];set sig [$net getSigType];set ni [llength [$net getITerms]];set nb [llength [$net getBTerms]];set wire [expr {[$net getWire] ne "NULL"}]
  if {$ni+$nb<2} {set cls SINGLE_TERMINAL_NO_EXTERNAL_NET_SPAN} elseif {$wire} {set cls MULTI_TERMINAL_WIRE_PRESENT_RC_GAP_REQUIRES_CHECK} else {set cls MULTI_TERMINAL_NO_WIRE_TOUCH_OR_MISSING_GEOMETRY_UNRESOLVED}
 }
 puts $output [join [list [dict get $wanted $key] $kind $inst $pin $nn $sig $ni $nb $wire $cls] "\t"]
}
set b [ord::get_db_block]
foreach p [$b getBTerms] {if {[$p getIoType] in {INPUT INOUT}} {observe_driver [$p getName] BTERM {} [$p getName] [$p getNet]}}
foreach i [$b getInsts] {foreach p [$i getITerms] {if {[$p getSigType] in {POWER GROUND} || [$p getIoType] ni {OUTPUT INOUT}} {continue};observe_driver "[$i getName]/[[$p getMTerm] getName]" ITERM [$i getName] [[$p getMTerm] getName] [$p getNet]}}
close $output
set f [open UNMATCHED w];dict for {key original} $wanted {if {![dict exists $seen $key]} {puts $f $original}};close $f
puts "NATIVE_UNANNOTATED_DRIVERS_RESOLVED [dict size $seen] OF [dict size $wanted]"
'''.replace('UNMATCHED',tcl(out/'unresolved_display_names.txt'))
        script=out/'audit.tcl';script.write_text(body+'\n')
        common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
        r['native_returncode']=execute(common,script,out/'native.log',threads=1);assert r['native_returncode']==0
        rows=list(csv.DictReader((out/'all_reported_drivers.tsv').open(),delimiter='\t'))
        unresolved=(out/'unresolved_display_names.txt').read_text().splitlines();assert len(rows)+len(unresolved)==count
        r['actual_classification_counts']=dict(Counter(p['classification'] for p in rows));r['all_display_names_resolved']=not unresolved
        r['unresolved_names_count']=len(unresolved)
        r['representative_objects_by_class']={c:[p for p in rows if p['classification']==c][:3] for c in r['actual_classification_counts']}
        r['interpretation']='No connected-net RC gap is waived; single-terminal and disconnected outputs have no interterminal conductor span in the actual native DB. Any multi-terminal case needs separate geometry and extractor diagnosis. No original checks removed.'
    except Exception:r['actual_failure']=traceback.format_exc();traceback.print_exc()
    r['all_closed_sources_unchanged']=all(sha(Path(p))==v for p,v in inputs.items());r['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    r['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'}
    (out/'execution.json').write_text(json.dumps(r,indent=2)+'\n')
    return int(bool(r.get('actual_failure')) or not r['all_closed_sources_unchanged'] or not r.get('all_display_names_resolved'))
if __name__=='__main__':sys.exit(run(sys.argv[1]))
