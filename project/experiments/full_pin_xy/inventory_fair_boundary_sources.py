"""Check old optimized perimeter sources before repeating any baseline route.

Exact native fingerprint/PG/die and SDC matches permit leaf-result reuse only.
Different hashes mean not yet proved equal, not necessarily unequal resources.
No two independent old systems are relabeled a common frozen base.
"""
from pathlib import Path
import datetime,json,os,re,sys,traceback
from run_exports import ROOT,sha
from run_common_integration import CASES,source_view,actual_boundary_pins
DRIVER=Path(__file__).resolve().parent
C={'act':'finalized/act-access-r03/act-C','mxu':'mxu_actual_via_tip/r01','opentpu_aux':'system_stacked_via_route/r01/opentpu_aux-C','gemm':'antenna_incremental_eco/r01/gemm-C','vector':'vector_resume/r01','llaccel_aux':'llsys_wire_pin_retention/r01'}

def run(revision):
    out=ROOT/'fair_boundary_source_inventory'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'SAME_RESOURCE_PERIMETER_SOURCE_INVENTORY_NOT_SYSTEM_PPA_OR_FROZEN_BASE','driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],'full_qualification':False,'source_SHA':{},'cases':{}}
    def details(path):
        q=json.loads(path.read_text());rec['source_SHA'][str(path)]=sha(path)
        for key in ['legacy_RC_STA_receipt','source_receipt']:
            if key in q:
                child=Path(q[key]);x=json.loads(child.read_text());rec['source_SHA'][str(child)]=sha(child)
                if any(n.endswith('.cells.tsv') for n in q.get('files',q.get('outputs',{}))):break
                path,q=child,x
        idx=q.get('files',q.get('outputs',{}));result={'receipt':str(path),'native_DRC':q.get('fresh_DRC_count',q.get('independent_DRC_count'))}
        for suffix in ['cells.tsv','pdn.tsv','die.tsv']:
            names=[n for n in idx if n.endswith('.'+suffix)]
            names.sort(key=lambda n:(0 if n.startswith('actual_final.') else 1 if n.startswith('after_route.') else 2 if n.startswith('after.') else 3 if n.startswith('placed.') else 4,n))
            if names:
                p=path.parent/names[0];assert sha(p)==idx[p.name]['sha256'];rec['source_SHA'][str(p)]=sha(p);result[suffix]={'path':str(p),'sha256':sha(p)}
        if q.get('source_sdc'):
            p=Path(q['source_sdc']);expected=q.get('input_sha256',{}).get(str(p))
            assert expected and sha(p)==expected;rec['source_SHA'][str(p)]=expected;result['sdc']={'path':str(p),'sha256':expected}
        else:
            sdcs=[p for p in q.get('source_SHA',q.get('source_inputs_SHA',q.get('source_inputs',{}))) if str(p).endswith('.sdc')]
            if len(sdcs)==1:
                p=Path(sdcs[0]);value=q.get('source_SHA',q.get('source_inputs_SHA',q.get('source_inputs',{})))[str(p)];assert sha(p)==value;rec['source_SHA'][str(p)]=value;result['sdc']={'path':str(p),'sha256':value}
        return result
    for case in CASES:
        result={}
        try:
            old=source_view(case,'Aopt','original');current=ROOT/C[case];result['current_C']=details(current/'execution.json');result['old_Aopt']=details(old['receipt'])
            pins=actual_boundary_pins(old['directory']/'abstract.lef',case,'Aopt');result['all_optimized_perimeter_signal_pins']=len(pins)
            result['all_original_pin_shapes_M5_M6_and_perimeter_enforced']=True
            matches={k:bool(result['current_C'].get(k) and result['old_Aopt'].get(k) and result['current_C'][k]['sha256']==result['old_Aopt'][k]['sha256']) for k in ['cells.tsv','pdn.tsv','die.tsv','sdc']}
            result['exact_resource_constraint_fingerprint_matches']=matches
            result['status']='EXACT_NATIVE_RESOURCE_CONSTRAINT_PAIR_REUSE_OLD_AOPT_LEAF_ONLY' if all(matches.values()) else 'NEEDS_MATCHED_SOURCE_BOUNDARY_IMPLEMENTATION_OR_STRONGER_EQUIVALENCE_NOT_YET_PROVEN'
            if not all(matches.values()):result['not_a_proof_of_resource_inequality']='Byte hashes may differ due ordering, filler or true ECO; do not claim a difference without the next audit.'
        except Exception:result['actual_inventory_failure']=traceback.format_exc();result['status']='SOURCE_BINDING_UNRESOLVED_CONTINUE_OTHER_CASES'
        rec['cases'][case]=result;print('FAIR_SOURCE_CASE',case,result['status'],flush=True)
    rec['all_sources_unchanged']=all(sha(Path(p))==v for p,v in rec['source_SHA'].items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()};(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');return int(not rec['all_sources_unchanged'] or any(r.get('actual_inventory_failure') for r in rec['cases'].values()))
if __name__=='__main__':sys.exit(run(sys.argv[1]))
