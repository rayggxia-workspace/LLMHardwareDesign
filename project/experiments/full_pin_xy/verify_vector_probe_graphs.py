"""Reuse closed native full graphs to prove the new VECTOR buffer relation.

No repeated OpenROAD graph export or P&R. Every new cell must be a directed
acyclic identity buffer; every resized original must preserve its actual
Liberty logic/state. This is relative mapped digital evidence, not RTL or STA.
"""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,sha
from verify_mapped_eco import load
from buffer_graph_contract import compare

DRIVER=Path(__file__).resolve().parent


def run(revision):
    source=ROOT/'vector_clone_probe/r03';rp=source/'execution.json';p=json.loads(rp.read_text())
    assert p.get('completed_utc') and p['native_returncodes']=={'clone_heuristic_probe':0,'source_graph':0,'repaired_graph':0}
    assert p['all_closed_sources_unchanged'] and all(p['pin_PG_die_unchanged'].values())
    assert p['all_original_stateful_instances_and_Liberty_logic_state_contracts_preserved']
    files=[source/n for n in ['source.tsv.gz','repaired.tsv.gz','gate_repaired_NOT_LEGALIZED_OR_ROUTED.odb']]
    for f in files:assert sha(f)==p['files'][f.name]['sha256']
    reference=ROOT/'vector_resume/r01';q=json.loads((reference/'execution.json').read_text())
    assert p['source_SHA'][str(reference/'routed.odb')]==q['files']['routed.odb']['sha256']
    out=ROOT/'vector_probe_equivalence'/revision;out.mkdir(parents=True,exist_ok=False)
    inputs={str(f):sha(f) for f in files+[rp,reference/'execution.json']}
    rec={'scope':'WHOLE_MAPPED_RELATIVE_DIGITAL_PROOF_REUSED_NATIVE_GRAPHS_NOT_RTL_OR_PHYSICAL_QUALIFICATION',
      'source_SHA':inputs,'reference_source':'Current actual vector_resume/r01, not original RTL',
      'native_graphs_reused_by_exact_SHA_not_reexported':True,'RTL_equivalence':'NOT_EXECUTED',
      'memory_contract':'Same unchanged hard-memory contracts assumed, if present; no macro model fabrication',
      'new_route_RC_STA_legality':'NOT_EXECUTED','full_qualification':False,
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID']}
    try:
        lib='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
        common=['singularity','exec','--cleanenv','--home',str(ROOT/'home'),'--pwd',str(out)]
        raw=subprocess.check_output(common+[IMAGE,'cat',lib]);rec['actual_Liberty_SHA256']=hashlib.sha256(raw).hexdigest()
        assert rec['actual_Liberty_SHA256']==p['actual_typical_Liberty_SHA256']
        result=compare(*load(files[0]),*load(files[1]),raw.decode(),lib)
        (out/'digital_contract_details.json').write_text(json.dumps(result,indent=2)+'\n')
        rec['summary']={k:v for k,v in result.items() if k not in ['changed_original_master_contracts','new_buffer_master_contracts']}
        rec['relative_mapped_digital_contract_pass']=True
    except Exception:rec['relative_mapped_digital_contract_pass']=False;rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(k))==v for k,v in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={f.name:{'bytes':f.stat().st_size,'sha256':sha(f)} for f in out.iterdir() if f.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return 0 if rec['relative_mapped_digital_contract_pass'] and rec['all_closed_sources_unchanged'] else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
