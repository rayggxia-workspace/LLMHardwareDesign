"""Read closed real upper source and diagnose a new whole-net repair variable."""
from pathlib import Path
import datetime,json,os,re,sys,traceback
from run_exports import ROOT,sha
from plan_upper_whole_nets import plan
DRIVER=Path(__file__).resolve().parent
def run(revision):
    source=ROOT/'upper_branch_repair/r02/llaccel';rp=source/'execution.json';q=json.loads(rp.read_text());assert q.get('completed_utc') and q['fresh_DRC_count']==2 and q['all_closed_sources_unchanged']
    names=['branch_access.tsv.gz','after_branch.OBS.tsv','before_route.die.tsv'];paths=[source/n for n in names]
    for p in paths:assert sha(p)==q['files'][p.name]['sha256']
    tech=ROOT/'upper_layer_probe/r01/model/research12.tech.lef';text=tech.read_text()
    for layer in ['metal11','metal12']:
        block=re.search(r'^LAYER '+layer+r'\s.*?^END '+layer,text,re.M|re.S).group(0)
        assert re.search(r'PARALLELRUNLENGTH\s+0\.0000\s+2\.7000\s+4\.0000',block)
        for width,spaces in [('0.0000','0.8000 0.8000 0.8000'),('0.9000','0.8000 0.9000 0.9000'),('1.5000','0.8000 0.9000 1.5000')]:
            assert ('WIDTH '+width+' '+spaces) in ' '.join(block.split())
    proof=ROOT/'upper_cut_corner_probe/r03/execution.json';pq=json.loads(proof.read_text())
    assert pq.get('completed_utc') and pq['native_controls_prove_corner_square_test_was_overconservative'] and pq['all_sources_unchanged']
    assert pq['source_SHA'][str(tech)]==sha(tech)
    inputs={str(p):sha(p) for p in [rp,tech,proof]+paths};out=ROOT/'upper_whole_net_search'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'SOURCE_BOUND_WHOLE_UPPER_NET_REPAIR_SEARCH_NOT_IMPLEMENTATION','source_SHA':inputs,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],'full_qualification':False,'native_edit_DRC_RC_STA':'NOT_EXECUTED'}
    try:rec['geometric_result']=plan(*paths,out/'whole_net_result_NOT_IMPLEMENTED.json')
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==s for p,s in inputs.items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()};(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');return int(bool(rec.get('actual_failure')) or not rec.get('geometric_result',{}).get('solution'))
if __name__=='__main__':sys.exit(run(sys.argv[1]))
