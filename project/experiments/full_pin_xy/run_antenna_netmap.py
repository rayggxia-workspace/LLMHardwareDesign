"""Use completed native/GDS evidence to guide actual antenna repair; never waive it."""
from pathlib import Path
import datetime,json,os,subprocess,sys
from run_exports import ROOT,IMAGE,sha

DRIVER=Path(__file__).resolve().parent


def run(revision):
    source=ROOT/'streamout/costed-r02/gemm-C_ECO';p=source/'execution.json';j=json.loads(p.read_text())
    assert j['merge_returncode']==0 and j['available_deck_findings']==1460
    leaf=ROOT/'leaf_eco/r03/gemm-C';l=json.loads((leaf/'execution.json').read_text());native=leaf/'whole_access.tsv.gz'
    view=ROOT/'eco_views/r02/gemm-C/execution.json';v=json.loads(view.read_text())
    assert v['source_receipt_sha256']==sha(leaf/'execution.json') and v['source_geometry_sha256']==l['files']['routed.odb']['sha256']
    assert j['source_clean_execution_sha256']==sha(view)
    assert l['fresh_DRC_count']==0 and l['whole_signal_geometry']['pass'] and sha(native)==l['files'][native.name]['sha256']
    rdb=source/'diagnostic.lyrdb';assert sha(rdb)==j['files'][rdb.name]['sha256']
    out=ROOT/'antenna_netmap'/revision;out.mkdir(parents=True,exist_ok=False)
    spec={'RDB':str(rdb),'native_conductors':str(native),'top':'gemm_engine','expected_findings':1460,
      'standard_GDS':'/OpenROAD-flow-scripts/flow/platforms/nangate45/gds/NangateOpenCellLibrary.gds',
      'deck':'/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc'}
    (out/'input.json').write_text(json.dumps(spec,indent=2)+'\n')
    command=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out),
      '--env','PINXY_ANTENNA_MAP_OUT='+str(out),IMAGE,'klayout','-b','-r',str(DRIVER/'map_antenna_polygons.py')]
    inputs={str(q):sha(q) for q in [p,leaf/'execution.json',rdb,native]}
    with (out/'native.log').open('x') as f:rc=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT).returncode
    rec={'scope':'ANTENNA_REPAIR_INPUT_CORRELATION_NOT_PHYSICAL_REPAIR_OR_FULL_QUALIFICATION',
      'native_returncode':rc,'source_SHA':inputs,'all_sources_unchanged':all(sha(Path(k))==v for k,v in inputs.items()),
      'full_qualification':False,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
      'scheduler_job':os.environ['SLURM_JOB_ID'],'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    if (out/'correlation_summary.json').exists():rec['correlation_summary']=json.loads((out/'correlation_summary.json').read_text())
    rec['files']={q.name:{'bytes':q.stat().st_size,'sha256':sha(q)} for q in out.iterdir() if q.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');return rc


if __name__=='__main__':sys.exit(run(sys.argv[1]))
