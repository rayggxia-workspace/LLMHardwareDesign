"""Admission to computation only, never native DRC or leaf acceptance.

Fresh RC and an exactly unchanged baseline DRC allow independent native finish
and full LEC to run while complete geometry diagnostics are pending. The
existing sealer still refuses a proof with native_whole_drc_zero=False.
"""
import json


def evidence(root,sha):
    base=root/'work/YUZE-LU/143/r-input-hold'
    bindings={}
    def read_index(name):
        folder=base/name;index=json.loads((folder/'index.json').read_text())
        assert index['diagnostic_completed'] and not index['native_leaf_accepted']
        bindings[str((folder/'index.json').relative_to(root))]=sha(folder/'index.json')
        for name,digest in index['files'].items():
            assert sha(folder/name)==digest
            bindings[str((folder/name).relative_to(root))]=digest
        return folder,index
    rc,rc_index=read_index('geometry-137')
    result=json.loads((rc/'diagnostic.json').read_text())
    assert result['diagnostic_completed'] and result['source_bytes_unchanged'] and result['mode']=='fresh-rc'
    assert result['fresh_rc_all_zero'] and result['fresh_rc_counts']==dict(setup_checks=0,hold_checks=0,capacitance=0,slew=0,fanout=0)
    assert not result['qualified'] and not result['native_leaf_accepted']
    assert len(result['commands'])==1 and result['commands'][0]['returncode']==0
    candidate_index=base/'buffer-129/index.json'
    expected=json.loads(candidate_index.read_text())['large_remote_files']['candidate.odb']['sha256']
    bindings[str(candidate_index.relative_to(root))]=sha(candidate_index)
    candidate_inputs=[v for k,v in result['inputs'].items() if k.endswith('/outputs/129/candidate.odb')]
    assert candidate_inputs==[expected]
    old,index=read_index('geometry-130')
    assert index['exact_original_candidate_native_drc_reports_identical'] and index['native_drc_count']==822
    baseline=(old/'native-whole-drc.rpt').read_bytes()
    assert baseline.count(b'violation type:')==822
    from r_complete_native_check import control_evidence
    control,controls=control_evidence(root,sha)
    bindings[str((control/'index.json').relative_to(root))]=sha(control/'index.json')
    for name,digest in json.loads((control/'index.json').read_text())['files'].items():
        bindings[str((control/name).relative_to(root))]=digest
    return dict(passed=True,computation_only=True,candidate_odb_sha256=expected,
                baseline_report_sha256=sha(old/'native-whole-drc.rpt'),unresolved_native_drc_count=822,
                fresh_rc_all_counts_zero=True,actual_partition_controls_verified=True,
                qualified=False,native_leaf_accepted=False,bound_files=bindings,
                scope='Only permit independent native finish/full LEC computation; unresolved geometry is not accepted and the existing sealer remains closed'),baseline


def admit(root,candidate,sha):
    result,baseline=evidence(root,sha)
    assert sha(candidate/'candidate.odb')==result['candidate_odb_sha256']
    assert (candidate/'candidate-native-drc.rpt').read_bytes()==baseline
    return result
