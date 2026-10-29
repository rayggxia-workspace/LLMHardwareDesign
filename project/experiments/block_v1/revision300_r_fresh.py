"""Operand-prefetched R starts every native physical stage again."""
import json


def implement(root,out,cpus,run):
    from revision300_flow import implement as fresh
    from io_slots import file_sha
    policy=json.loads((root/'project/experiments/block_v1/revision300-r-fresh.json').read_text())
    assert policy==dict(schema='revision300-r-fresh/1',
        mapping='block-v1-20261029-342/tasks/revision300-map-r',
        function='block-v1-20261029-342/tasks/revision300-test-r',
        measurements=dict(revised='block-v1-20261029-342/tasks/revision300-bench-r-revised',
                          extended='block-v1-20261029-342/tasks/revision300-bench-r-extended'),
        inherited_physical_stages=[],requires_fresh_final_acceptance=True)
    relative='project/rtl/block_library_v1/block_v1_r.sv';current=file_sha(root/relative)
    for path in policy['measurements'].values():
        source=out.parents[2]/path;receipt=json.loads((source/'receipt.json').read_text())
        assert receipt['passed'] and receipt['mode']==source.name
        report=source/'revision300-vr-benchmark.json'
        assert file_sha(report)==receipt['outputs'][report.name]
        result=json.loads(report.read_text());assert result['passed']
        assert len(result['rtl_sha256'])==1 and next(iter(result['rtl_sha256'].values()))==current
    fresh(root,out,cpus,run,'r',prerequisite_tasks={k:policy[k]for k in ('mapping','function')})
