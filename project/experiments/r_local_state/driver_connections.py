"""Read exact native driver/load ownership for measured electrical violators."""
from pathlib import Path
import argparse,hashlib,json,subprocess
p=argparse.ArgumentParser();p.add_argument('--odb',type=Path,required=True);p.add_argument('--driver',action='append',required=True);a=p.parse_args()
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
before=sha(a.odb);O=Path.cwd()/'driver-connections';O.mkdir(exist_ok=False)
assert len(set(a.driver))==len(a.driver)and all('/'in n and not any(c in n for c in '{}\n\r\t')for n in a.driver)
t='set_thread_count 16\nread_db {'+str(a.odb)+'}\nset b [ord::get_db_block]\nset f [open connections.tsv w]\n'
for name in a.driver:
 inst,pin=name.rsplit('/',1)
 t+='set inst [$b findInst {'+inst+'}]\nif {$inst eq "NULL"} {error "Measured driver missing"}\n'
 t+='set p [$inst findITerm {'+pin+'}]\nif {$p eq "NULL"} {error "Measured driver pin missing"}\n'
 t+='''set net [$p getNet]
if {$net eq "NULL"} {error "Measured driver net missing"}
set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
puts $f [join [list DRIVER [$inst getName] [[$inst getMaster] getName] [[$p getMTerm] getName] [$net getName] [$net getSigType] [$inst getPlacementStatus] [$inst getLocation] $group] "\t"]
foreach term [$net getITerms] {
 set cell [$term getInst];set master [$cell getMaster];set mt [$term getMTerm];set group [$cell getGroup]
 if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list TERM [$cell getName] [$master getName] [$mt getName] [$mt getIoType] [$cell getPlacementStatus] [$cell getLocation] $group] "\t"]
}
foreach term [$net getBTerms] {puts $f [join [list PORT [$term getName] [$term getIoType]] "\t"]}
'''
t+='close $f\n';(O/'probe.tcl').write_text(t)
with(O/'probe.log').open('w')as log:r=subprocess.run(['openroad','-no_init','-exit','probe.tcl'],cwd=O,stdout=log,stderr=subprocess.STDOUT)
assert sha(a.odb)==before
result=dict(passed=r.returncode==0,odb=str(a.odb),odb_sha256=before,drivers=a.driver,probe_sha256=sha(O/'probe.tcl'),artifacts={f.name:dict(sha256=sha(f),bytes=f.stat().st_size)for f in O.iterdir()if f.is_file()},scope='Read-only native connectivity/master/placement/group inventory; no timing or qualification transfer.')
(O/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');raise SystemExit(r.returncode)
