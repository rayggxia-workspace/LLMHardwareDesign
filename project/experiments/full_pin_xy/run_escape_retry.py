"""Try detailed routing despite coarse GRT overflow, without rule relaxation.

Reuse each failed fixture's actual placed/PG checkpoint and exact landing
coordinates. Only guide generation may contain overflow. GRT overflow remains
reported; full independent DRC/connectivity/PG gates are still mandatory.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import datetime, json, os, re, shutil, sys, traceback
from run_exports import ROOT, IMAGE, BIN, sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from check_access import check

DRIVER = Path(__file__).resolve().parent


def one(case, variant, source_revision, revision):
    source = ROOT/'escape_fixtures'/source_revision/(case+'-'+variant)
    old = json.loads((source/'execution.json').read_text())
    assert old['native_route_returncode'] != 0 and 'GRT-0116' in (source/'route.log').read_text()
    out = ROOT/'escape_fixtures'/revision/(case+'-'+variant)
    out.mkdir(parents=True, exist_ok=False)
    inputs = {str(source/p):sha(source/p) for p in ['execution.json','placed.odb','route.tcl','landing_ports.csv','setup.log']}
    shutil.copyfile(source/'placed.odb',out/'placed.odb')
    shutil.copyfile(source/'landing_ports.csv',out/'landing_ports.csv')
    text=(source/'route.tcl').read_text()
    assert text.count('global_route -guide_file')==1
    text=text.replace(str(source),str(out)).replace('global_route -guide_file','global_route -allow_congestion -guide_file')
    (out/'route.tcl').write_text(text)
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    env='PINXY_DRIVER={},PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT={}'.format(DRIVER,out/'whole_access.tsv.gz')
    code=execute(common,out/'route.tcl',out/'route.log',env)
    rec={'scope':'REAL_PARENT_M10_ESCAPE_RETRY_NOT_COMMON_BASE_OR_SYSTEM_QUALIFICATION','case':case,'variant':variant,
         'source_failed_fixture':str(source),'source_inputs_SHA':inputs,'native_route_returncode':code,
         'global_router_overflow_allowed_for_guide_only':True,'GRT_overflow_is_not_reclassified_as_pass':True,
         'all_OBS_geometry_rules_and_routing_layers_unchanged':True,'exact_previous_placed_geometry':sha(out/'placed.odb')==inputs[str(source/'placed.odb')],
         'same_previous_256_parent_M10_landing_ports':sha(out/'landing_ports.csv')==inputs[str(source/'landing_ports.csv')],
         'full_qualification':False,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID']}
    if code==0:
        fresh=out/'fresh.tcl'
        fresh.write_text('read_db '+tcl(out/'routed.odb')+'\nset_routing_layers -signal metal2-metal10 -clock metal4-metal10\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
        rec['independent_DRC_returncode']=execute(common,fresh,out/'independent.log',threads=1)
        p=out/'independent.drc'
        rec['independent_DRC_count']=len(re.findall(r'^violation type:',p.read_text(),re.M)) if rec['independent_DRC_returncode']==0 and p.exists() else None
        rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
    rec['source_unchanged']=all(sha(Path(p))==h for p,h in inputs.items())
    rec['RC_STA']='Not executed; original leaf source model/STA/full-rule failures retained, not inferred from guide/route completion'
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in out.iterdir() if p.is_file()}
    rec['status']='ESCAPE_GEOMETRY_GATES_PASSED_GRT_OVERFLOW_RETAINED_NOT_SYSTEM_QUALIFIED' if code==0 and rec.get('independent_DRC_count')==0 and rec.get('whole_signal_geometry',{}).get('pass') else 'ACTUAL_ESCAPE_RETRY_FAILED_OR_INCOMPLETE'
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    print('ESCAPE_RETRY',case,variant,rec['status'],flush=True)
    return rec['status'].startswith('ESCAPE_GEOMETRY_GATES_PASSED')


def safe(args):
    out=ROOT/'escape_fixtures'/args[3]/(args[0]+'-'+args[1])
    if out.exists():return False
    try:return one(*args)
    except Exception:
        traceback.print_exc();out.mkdir(parents=True,exist_ok=True)
        with (out/'driver_failure.json').open('x') as f:f.write(json.dumps({'status':'FAILED_NOT_QUALIFIED','traceback':traceback.format_exc()},indent=2)+'\n')
        return False


if __name__=='__main__':
    assert int(os.environ['SLURM_CPUS_PER_TASK'])>=8
    case,source_revision,revision=sys.argv[1:4]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(safe,[(case,v,source_revision,revision) for v in ['Aopt','C']]))
    sys.exit(0 if all(results) else 1)
