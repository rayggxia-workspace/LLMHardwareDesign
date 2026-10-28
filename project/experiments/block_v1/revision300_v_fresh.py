"""Corrected V starts every physical stage again; never reads old CTS data."""
import json


def implement(root,out,cpus,run):
    from revision300_flow import implement as fresh
    policy=json.loads((root/'project/experiments/block_v1/revision300-v-fresh.json').read_text())
    assert policy==dict(schema='revision300-v-fresh/1',
        mapping='block-v1-20261029-289/tasks/revision300-map-v',
        function='block-v1-20261029-289/tasks/revision300-test-v',
        upper_layer_adjustment=.20,congestion_iterations=100,
        inherited_physical_stages=[],requires_fresh_final_acceptance=True)
    fresh(root,out,cpus,run,'v',prerequisite_tasks={k:policy[k]for k in ('mapping','function')},
          routing_policy={k:policy[k]for k in ('upper_layer_adjustment','congestion_iterations')})
