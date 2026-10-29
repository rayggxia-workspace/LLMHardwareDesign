"""Classify every remaining pin from actual net/endpoint records, read-only."""
from pathlib import Path
from collections import Counter
import csv,datetime,json,os,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute

DRIVER=Path(__file__).resolve().parent


def run(revision):
    audit=ROOT/'all_llsys_actual_access_caps/r02';rp=audit/'execution.json';prior=json.loads(rp.read_text())
    assert prior.get('completed_utc') and prior['native_read_only_returncode']==0 and prior['all_closed_sources_unchanged']
    table=audit/'all13507_actual_own_via_candidates.tsv';assert sha(table)==prior['files'][table.name]['sha256']
    selected=[r for r in csv.DictReader(table.open(),delimiter='\t') if not r['candidate_x'] and r['aligned_preferred']=='0']
    assert len(selected)==87
    source=ROOT/'llsys_parent_tip_views/r01/llaccel_aux-C';sp=source/'execution.json';q=json.loads(sp.read_text());odb=source/'clean.odb'
    assert q.get('completed_utc') and sha(odb)==q['files'][odb.name]['sha256']==prior['source_geometry_SHA256']
    inputs={str(p):sha(p) for p in [rp,table,sp,odb]}
    out=ROOT/'llsys_residual_pin_audit'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'ALL87_RESIDUAL_SIGNAL_PIN_ACTUAL_NET_AND_ENDPOINT_READ_ONLY_AUDIT_NOT_REPAIR',
         'source_SHA':inputs,'full_qualification':False,'scheduler_job':os.environ['SLURM_JOB_ID'],
         'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
         'not_checked':['New access point or routing','Full rules/PG/AP','RC/STA or whole-design equivalence']}
    try:
        body='''set b [ord::get_db_block]
set f [open SUMMARY w];puts $f "pin\tnet\tuse\tinternal_ITerms\ttop_BTerms\thas_native_wire\tactual_top_names"
set g [open ENDPOINTS w];puts $g "pin\tnet\tinstance\tport\tlayer\tx0\ty0\tx1\ty1"
foreach pin PINS {
 set bt [$b findBTerm $pin];if {$bt eq "NULL"} {error "Residual original pin missing"};set n [$bt getNet]
 set names {};foreach term [$n getBTerms] {lappend names [$term getName]}
 puts $f [join [list $pin [$n getName] [$bt getSigType] [llength [$n getITerms]] [llength [$n getBTerms]] [expr {[$n getWire] ne "NULL"}] [join $names {;}]] "\t"]
 foreach it [$n getITerms] {foreach geometry [$it getGeometries] {
  lassign $geometry ly z;puts $g [join [list $pin [$n getName] [[$it getInst] getName] [[$it getMTerm] getName] [$ly getName] [$z xMin] [$z yMin] [$z xMax] [$z yMax]] "\t"]
 }}
};close $f;close $g
puts ACTUAL_ALL87_NET_ENDPOINTS_READ_ONLY_NOT_ACCESS_PASS
'''.replace('SUMMARY',tcl(out/'all87_actual_net_classes.tsv')).replace('ENDPOINTS',tcl(out/'all87_actual_internal_endpoints.tsv')).replace('PINS',tcl(' '.join(r['pin'] for r in selected)))
        script=out/'read_residual.tcl';script.write_text('read_db '+tcl(odb)+'\n'+body)
        common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
        rec['native_read_only_returncode']=execute(common,script,out/'native.log',threads=1)
        assert rec['native_read_only_returncode']==0
        rows=list(csv.DictReader((out/'all87_actual_net_classes.tsv').open(),delimiter='\t'))
        assert len(rows)==87 and {r['pin'] for r in rows}=={r['pin'] for r in selected}
        rec['actual_class_counts']=dict(Counter('NO_NATIVE_WIRE_NO_INTERNAL_PEER_SINGLE_BTERM' if r['has_native_wire']=='0' and r['internal_ITerms']=='0' and r['top_BTerms']=='1' else 'HAS_REAL_CONNECTION_REQUIRES_ACCESS_REPAIR' for r in rows))
        rec['all_87_original_pins_retained']=True
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==s for p,s in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return 0 if not rec.get('actual_failure') and rec['all_closed_sources_unchanged'] else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
