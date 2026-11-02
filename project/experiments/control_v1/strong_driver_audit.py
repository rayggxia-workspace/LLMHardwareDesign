"""Read actual final output driver cells; never infer retained drive from RTL."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path


def audit(odb,out,expected=None):
    assert os.environ.get('SLURM_JOB_ID')and len(os.sched_getaffinity(0))<=16
    def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
    before=sha(odb);script=out/'strong-driver-audit.tcl';table=out/'strong-driver-audit.tsv'
    script.write_text('set_thread_count 16\nread_db {'+str(odb)+'}\nset f [open {'+str(table)+'} w]\n'+r'''
foreach port [[ord::get_db_block] getBTerms] {
 if {[$port getSigType] in {POWER GROUND} || [$port getIoType] ne "OUTPUT"} {continue}
 set drivers {}
 foreach term [[$port getNet] getITerms] {
  if {[[$term getMTerm] getIoType] eq "OUTPUT"} {lappend drivers $term}
 }
 if {[llength $drivers]!=1} {error "Actual output driver count"}
 set term [lindex $drivers 0];set inst [$term getInst];set master [[$inst getMaster] getName]
 if {$master ne "BUF_X32" || ![string match control_output_driver_* [$inst getName]]} {error "Strong output stage was replaced"}
 puts $f "[$port getName]\t[$inst getName]\t$master\t[[$term getMTerm] getName]"
}
close $f
''')
    with (out/'strong-driver-audit.log').open('w')as f:subprocess.run(['openroad','-no_init','-exit',script],stdout=f,stderr=subprocess.STDOUT,check=True)
    assert before==sha(odb),'Read-only driver audit changed native database'
    rows=[line.split('\t')for line in table.read_text().splitlines()]
    assert rows and all(len(r)==4 and r[2:] ==['BUF_X32','Z']for r in rows)
    assert len(set(r[0]for r in rows))==len(rows)
    if expected is not None:assert len(rows)==expected,(len(rows),expected)
    return dict(passed=True,output_count=len(rows),all_actual_drivers_BUF_X32=True,odb=str(odb),odb_sha256=before,
                table=str(table),table_sha256=sha(table),helper_sha256=sha(Path(__file__)),no_database_mutation=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--odb',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    r=dict(passed=False,scope='Actual output driver inventory only; no timing or system qualification.')
    try:r.update(audit(a.odb,a.out))
    finally:(a.out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
