"""Whole mapped digital relation with directed, acyclic identity-buffer cones.

Original instance contracts and every original endpoint must remain. New cells
are accepted only as proven identity buffers, with directed reachability from
the same original drivers. Undriven/null terminals are never silently unioned.
This is conditional on unchanged memory contracts, not an RTL or analog proof.
"""
from pathlib import Path
from collections import defaultdict,deque
import datetime,json,os,subprocess,sys,traceback
from run_exports import ROOT,CFG,IMAGE,sha
from verify_mapped_eco import load,export_graph
from cell_semantics import check_pair,contract

DRIVER=Path(__file__).resolve().parent


from buffer_graph_contract import compare


def run(revision,case='opentpu_aux'):
    assert case in ['opentpu_aux','vector']
    view=ROOT/('eco_views/r03/opentpu_aux-C' if case=='opentpu_aux' else 'vector_resume/r01')
    vp=view/'execution.json';v=json.loads(vp.read_text())
    reference=Path(CFG['physical_blocks'][case]['odb']);current=view/('clean.odb' if case=='opentpu_aux' else 'routed.odb')
    assert v.get('completed_utc') and sha(reference)==CFG['physical_blocks'][case]['expected_sha256']
    if case=='opentpu_aux':
        assert v['native_export_returncode']==0 and v['SPEF_replay_matches_source'] and sha(current)==v['source_geometry_sha256']
    else:
        assert v['native_returncodes']['route']==0 and v['fresh_DRC_count']==0 and v['whole_signal_geometry']['pass']
        assert all(v['source_pin_PG_die_unchanged'].values()) and v['all_sources_unchanged']
        assert sha(current)==v['files']['routed.odb']['sha256']
    out=ROOT/'buffered_equivalence'/revision/case;out.mkdir(parents=True,exist_ok=False)
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
      '--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
      '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
      '--home',str(ROOT/'home'),'--pwd',str(out)]
    inputs={str(p):sha(p) for p in [reference,current,vp]}
    rec={'scope':'WHOLE_MAPPED_DIGITAL_RELATION_WITH_DIRECTED_IDENTITY_BUFFER_CONES',
      'memory_contract':'Identical original hard-memory instances and all terminals; same memory semantics assumed',
      'RTL_formal_equivalence':'NOT_EXECUTED','analog_RC_STA_electrical_equivalence':'NOT_CLAIMED',
      'complete_rules':'NOT_QUALIFIED','full_qualification':False,'source_SHA':inputs,
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID']}
    try:
        codes=[export_graph(common,source,out,label) for source,label in [(reference,'reference'),(current,'costed_C')]]
        rec['native_export_codes']=codes;assert codes==[0,0]
        lib='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
        text=subprocess.check_output(common+[IMAGE,'cat',lib]).decode()
        result=compare(*load(out/'reference.tsv.gz'),*load(out/'costed_C.tsv.gz'),text,lib)
        (out/'digital_contract_details.json').write_text(json.dumps(result,indent=2)+'\n')
        rec['relative_mapped_digital_contract_pass']=True
        rec['summary']={k:v for k,v in result.items() if k not in ['changed_original_master_contracts','new_buffer_master_contracts']}
    except Exception:
        rec['relative_mapped_digital_contract_pass']=False;rec['actual_failure']=traceback.format_exc();traceback.print_exc()
    rec['all_sources_unchanged']=all(sha(Path(k))==v for k,v in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');print('BUFFERED_MAPPED_CONTRACT',rec['relative_mapped_digital_contract_pass'],flush=True)
    return 0 if rec['relative_mapped_digital_contract_pass'] and rec['all_sources_unchanged'] else 1


if __name__=='__main__':sys.exit(run(*sys.argv[1:3]))
