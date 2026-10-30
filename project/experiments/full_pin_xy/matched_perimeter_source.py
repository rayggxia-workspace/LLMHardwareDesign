"""Choose only source-matched perimeter leaves; never infer system fairness."""
import json
from run_exports import ROOT,sha


def select(case,scheme,original):
    assert scheme=='Aopt'
    inventory=ROOT/'fair_boundary_source_inventory/r01/execution.json'
    q=json.loads(inventory.read_text())
    assert q.get('completed_utc') and q['all_sources_unchanged']
    proof=q['cases'][case]
    if case in ['act','mxu','llaccel_aux']:
        assert proof['status']=='EXACT_NATIVE_RESOURCE_CONSTRAINT_PAIR_REUSE_OLD_AOPT_LEAF_ONLY'
        assert all(proof['exact_resource_constraint_fingerprint_matches'].values())
        for side in ['current_C','old_Aopt']:
            for key in ['cells.tsv','pdn.tsv','die.tsv','sdc']:
                row=proof[side][key];assert sha(row['path'])==row['sha256']
        value=original(case,scheme,'original')
    else:
        folder=ROOT/'same_source_perimeter_views/r01'/(case+'-Aopt')
        rp=folder/'execution.json';v=json.loads(rp.read_text())
        assert v.get('completed_utc') and not v.get('actual_failure') and v['all_closed_sources_unchanged']
        assert v['native_export_returncode']==v['fresh_model_read_returncode']==0
        assert v['matching_all_signal_model_pins']=={'gemm':3753,'vector':2246,'opentpu_aux':2229}[case]
        assert v['all_current_signal_and_PG_pin_rows_exact'] and v['SPEF_replay_matches_source']
        source=v['source_receipt'];s=json.loads(open(source).read())
        assert sha(source)==v['source_SHA'][source]
        assert s.get('completed_utc') and not s.get('actual_failure') and s['fresh_DRC_count']==0
        assert all(s['exact_C_resource_cells_connections_poses_PG_and_die_preserved'].values())
        assert s['all_closed_sources_unchanged'] and s['whole_signal_geometry']['pass']
        for p in ['clean.odb','abstract.lef','detailed.lef','timing.lib','pins.tsv']:
            assert sha(folder/p)==v['files'][p]['sha256']
        assert sha(folder/'clean.odb')==v['source_geometry_sha256']
        value={'directory':folder,'receipt':rp,'ODB':folder/'clean.odb','model':folder/'timing.lib',
               'model_receipt':rp,'native_DRC':0,'complete_rules':'NOT_QUALIFIED','RTL_equivalence':'NOT_EXECUTED'}
    value['source_profile']='matched_perimeter'
    value['resource_match_inventory']=inventory
    return value
