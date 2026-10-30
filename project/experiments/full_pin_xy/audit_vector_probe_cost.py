"""Separate real nonfiller ECO cost from reused filler instance names.

Read completed native cost tables; never rerun optimization or mutate a receipt.
"""
from pathlib import Path
from collections import Counter
import csv,datetime,json,os,sys,traceback
from run_exports import ROOT,sha

DRIVER=Path(__file__).resolve().parent


def run(revision):
    old=ROOT/'vector_resume/r01';new=ROOT/'vector_probe_route/r01'
    receipts=[old/'execution.json',new/'execution.json'];qs=[json.loads(p.read_text()) for p in receipts]
    assert qs[1].get('completed_utc') and qs[1]['all_sources_unchanged']
    paths=[p/'actual_final.cell_cost.tsv' for p in [old,new]]
    for p,q in zip(paths,qs):assert sha(p)==q['files'][p.name]['sha256']
    out=ROOT/'vector_probe_cost_audit'/revision;out.mkdir(parents=True,exist_ok=False)
    inputs={str(p):sha(p) for p in paths+receipts}
    rec={'scope':'CLOSED_NATIVE_COST_CATEGORY_AUDIT_NOT_NEW_PHYSICAL_IMPLEMENTATION',
         'source_SHA':inputs,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
         'scheduler_job':os.environ['SLURM_JOB_ID'],'full_qualification':False}
    try:
        def read(path):
            with path.open() as f:return {r['instance']:(r['master'],r['type'],r['x_dbu'],r['y_dbu'],float(r['area_um2'])) for r in csv.DictReader(f,delimiter='\t')}
        a,b=map(read,paths);common=set(a)&set(b)
        changed=Counter();moved=Counter();details=[]
        for n in common:
            x,y=a[n],b[n];cat='CORE_SPACER' if x[1]==y[1]=='CORE_SPACER' else 'NONFILLER'
            assert (x[1]=='CORE_SPACER')==(y[1]=='CORE_SPACER'),'Unexpected physical/logical type conversion'
            if x[0]!=y[0]:changed[cat]+=1
            if x[2:4]!=y[2:4]:moved[cat]+=1
            if cat=='NONFILLER' and (x[0]!=y[0] or x[2:4]!=y[2:4]):
                details.append({'instance':n,'source_master':x[0],'actual_master':y[0],
                   'source_type':x[1],'actual_type':y[1],'master_changed':x[0]!=y[0],
                   'position_changed':x[2:4]!=y[2:4]})
        cost=qs[1]['separate_cell_ECO_cost']
        assert sum(changed.values())==cost['changed_master_original_instances']
        assert sum(moved.values())==cost['moved_original_instances']
        added=sum(b[n][1]!='CORE_SPACER' for n in set(b)-set(a));removed=sum(a[n][1]!='CORE_SPACER' for n in set(a)-set(b))
        assert added==cost['added_functional_instances_excluding_fillers'] and removed==cost['removed_functional_instances_excluding_fillers']
        area=lambda rows:sum(r[4] for r in rows.values() if r[1] not in ['BLOCK','CORE_SPACER'])
        delta=area(b)-area(a);assert abs(delta-cost['standard_cell_master_area_delta_um2'])<1e-6
        rec.update({'changed_master_original_NONFILLER_instances':changed['NONFILLER'],
          'changed_master_reused_CORE_SPACER_names':changed['CORE_SPACER'],
          'moved_original_NONFILLER_instances':moved['NONFILLER'],
          'moved_reused_CORE_SPACER_names':moved['CORE_SPACER'],
          'added_NONFILLER_instances':added,'removed_NONFILLER_instances':removed,
          'standard_cell_master_area_delta_um2_excluding_BLOCK_and_CORE_SPACER':delta,
          'all_original_uncategorized_cost_counts_reproduced':True,
          'not_block_area_saving_or_pure_pin_XY':True,
          'timing_status_unchanged':'Native0/connected/PG/RC done, setup -4.148930ns still FAILED'})
        with (out/'all_changed_or_moved_original_NONFILLER_cells.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(details[0]));w.writeheader();w.writerows(sorted(details,key=lambda r:r['instance']))
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==s for p,s in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return 0 if rec.get('all_original_uncategorized_cost_counts_reproduced') and rec['all_closed_sources_unchanged'] else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
