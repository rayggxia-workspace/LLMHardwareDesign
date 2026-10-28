"""Read-only source NDR and failing-driver audit; never edit live jobs/databases."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys
from concurrent.futures import ThreadPoolExecutor
from run_exports import ROOT,CFG,IMAGE,BIN,sha
from run_parent_trial import tcl

DRIVER=Path(__file__).resolve().parent


def one(name,path,drivers,out):
    odb=Path(path);directory=out/name;directory.mkdir();before=sha(odb)
    script=directory/'audit.tcl'
    commands=['read_db '+tcl(odb),
        'set b [ord::get_db_block];set f [open '+tcl(directory/'net_ndr.tsv')+' w];puts $f "net\\tsig_type\\tNDR"',
        'foreach n [$b getNets] {set d [$n getNonDefaultRule];if {$d ne "NULL"} {puts $f [join [list [$n getName] [$n getSigType] [$d getName]] "\\t"]}};close $f',
        'set f [open '+tcl(directory/'NDR_rules.tsv')+' w];puts $f "rule\\thard_spacing\\tlayer\\twidth_dbu\\tspacing_dbu"',
        '''foreach d [[ord::get_db_tech] getNonDefaultRules] {
 set hard UNKNOWN;catch {set hard [$d getHardSpacing]}
 foreach lr [$d getLayerRules] {puts $f [join [list [$d getName] $hard [[$lr getLayer] getName] [$lr getWidth] [$lr getSpacing]] "\\t"]}
};close $f''',
        'set f [open '+tcl(directory/'drivers.tsv')+' w];puts $f "pin\\tmaster\\tmaster_type\\twidth_dbu\\tnet\\tinst_dont_touch\\tnet_dont_touch\\tBTerms\\tITerms"']
    for full in drivers:
        inst,pin=full.rsplit('/',1)
        commands+=['set i [$b findInst '+tcl(inst)+'];if {$i eq "NULL"} {error "Unknown actual driver"}',
          'set it [$i findITerm '+tcl(pin)+'];set m [$i getMaster];set n [$it getNet];set idt UNKNOWN;set ndt UNKNOWN;catch {set idt [$i isDoNotTouch]};catch {set ndt [$n isDoNotTouch]}',
          'puts $f [join [list '+tcl(full)+' [$m getName] [$m getType] [$m getWidth] [$n getName] $idt $ndt [llength [$n getBTerms]] [llength [$n getITerms]]] "\\t"]']
    commands+=['close $f','puts "READ_ONLY_NDR_DRIVER_AUDIT_FINISHED"']
    script.write_text('\n'.join(commands)+'\n')
    command=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
             '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro','--home',str(ROOT/'home'),'--pwd',str(directory),IMAGE,BIN,'-threads','1','-no_init','-exit',str(script)]
    with (directory/'native.log').open('x') as f:result=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT)
    rec={'scope':'READ_ONLY_NDR_AND_DRIVER_AUDIT_NOT_PHYSICAL_QUALIFICATION','source':str(odb),'source_SHA':before,'source_unchanged':before==sha(odb),
         'native_returncode':result.returncode,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
         'full_qualification':False,'files':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in directory.iterdir() if p.is_file()}}
    (directory/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return rec


def run(revision):
    assert int(os.environ['SLURM_CPUS_PER_TASK'])>=2
    out=ROOT/'constraint_audit'/revision;out.mkdir(parents=True,exist_ok=False)
    jobs=[('ll_original',CFG['physical_blocks']['llaccel_aux']['odb'],[]),
          ('ll_pg_full_C',str(ROOT/'finalized/llsys-pg-r03/llaccel_aux-C/clean.odb'),[]),
          ('gemm_access',str(ROOT/'finalized/access-r03/gemm-C/clean.odb'),['place15450/Z','_328297_/Z','rq_m[341]$_DFFE_PN0P_/Q']),
          ('mxu_access',str(ROOT/'finalized/access-r03/mxu-C/clean.odb'),['place10281/Z'])]
    with ThreadPoolExecutor(max_workers=2) as pool:records=list(pool.map(lambda j:one(*j,out),jobs))
    # Installed source is primary evidence for the warning. Missing source is
    # recorded; do not infer the installed behavior from a newer online build.
    command=['singularity','exec','--cleanenv','--home',str(ROOT/'home'),IMAGE,'sh','-c',
       'for d in /OpenROAD-flow-scripts/tools/OpenROAD/src/grt/src /OpenROAD/src/grt/src; do if [ -d "$d" ]; then grep -n -B 8 -A 12 -F "Disabled NDR" "$d"/*.cpp || true; fi; done; sha256sum /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad']
    with (out/'installed_GRT_source_excerpt.txt').open('x') as f:subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,check=True)
    (out/'execution.json').write_text(json.dumps({'scope':'READ_ONLY_SOURCE_AND_NDR_AUDIT','records':records,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'full_qualification':False,'not_claimed':['NDR actual width/spacing passed','live in-memory GRT constraints unchanged','STA/electrical pass']},indent=2)+'\n')
    print('CONSTRAINT_AUDIT_FINISHED',[(j['native_returncode'],j['source_unchanged']) for j in records],flush=True)


if __name__=='__main__':run(sys.argv[1])
