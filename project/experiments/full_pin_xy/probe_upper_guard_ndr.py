"""Installed-tool NDR API probe; no routing or physical-pass claim."""
from pathlib import Path
import csv,datetime,json,os,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute

DRIVER=Path(__file__).resolve().parent


def guard_tcl(out):
    return '''puts "ACTUAL_CREATE_NDR_TCL_BODY [info body create_ndr]"
puts "ACTUAL_SET_NDR_RULES_TCL_BODY [info body set_ndr_rules]"
create_ndr -name HPY_UPPER_GUARD_15 -width {metal11 0.8 metal12 0.8} -spacing {metal11 1.5 metal12 1.5}
set guard NULL
foreach rule [[ord::get_db_block] getNonDefaultRules] {if {[$rule getName] eq "HPY_UPPER_GUARD_15"} {set guard $rule}}
if {$guard eq "NULL"} {error "Actual native NDR creation not found"}
$guard setHardSpacing 1
if {![$guard getHardSpacing]} {error "Conservative NDR hard spacing not retained"}
set f [open '''+tcl(Path(out)/'actual_NDR_layer_rules.tsv')+''' w]
puts $f "layer\twidth_DBU\tspacing_DBU"
foreach layer [[ord::get_db_tech] getLayers] {set rule [$guard getLayerRule $layer];if {$rule ne "NULL"} {puts $f [join [list [$layer getName] [$rule getWidth] [$rule getSpacing]] "\t"]}}
close $f
set count 0
foreach net [[ord::get_db_block] getNets] {$net setNonDefaultRule $guard;if {[$net getNonDefaultRule] ne $guard} {error "Native NDR assignment mismatch"};incr count}
if {$count!=770} {error "Expected all original 770 branch nets"}
puts "ACTUAL_NATIVE_GUARD_ASSIGNED_770_NOT_ROUTED"
'''


def run(revision):
    source=ROOT/'upper_adaptation_trial/r02/llaccel/placed_adapter_NOT_SYSTEM.odb'
    rp=source.parent/'execution.json';q=json.loads(rp.read_text());assert sha(source)==q['files'][source.name]['sha256']
    out=ROOT/'upper_guard_api'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'NATIVE_API_PROBE_ONLY_NOT_ACTUAL_ROUTING_OR_DRC',
         'source_SHA':{str(p):sha(p) for p in [source,rp]},'full_qualification':False,
         'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
         'guard_rule_um':{'width_M11_M12':.8,'spacing_M11_M12':1.5},
         'documentation_source':'https://openroad.readthedocs.io/en/latest/main/src/odb/README.html#create-ndr',
         'not_checked':['Actual routing','Original and NDR DRC','Pin access','Full system function/RC/STA']}
    try:
        script=out/'probe.tcl';script.write_text('read_db '+tcl(source)+'\n'+guard_tcl(out))
        common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
        rec['native_probe_returncode']=execute(common,script,out/'native.log',threads=1)
        if rec['native_probe_returncode']==0:
            with (out/'actual_NDR_layer_rules.tsv').open() as f:rules={r['layer']:r for r in csv.DictReader(f,delimiter='\t')}
            assert all(int(rules[ly]['width_DBU'])==1600 and int(rules[ly]['spacing_DBU'])==3000 for ly in ['metal11','metal12'])
            rec['actual_rule_readback_and_all770_assignment_verified']=True
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==h for p,h in rec['source_SHA'].items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return 0 if rec.get('actual_rule_readback_and_all770_assignment_verified') and rec['all_closed_sources_unchanged'] else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
