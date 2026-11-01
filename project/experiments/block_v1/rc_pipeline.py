"""Explicit immutable run bindings for the current research calibration attempt."""
import json
import re


def configuration(root):
    value=json.loads((root/'project/experiments/block_v1/rc_calibration.json').read_text())
    assert value['schema']=='block-v1-rc-pipeline/1'
    for name in ['patterns_run','prepare_run','solver_run','pilot_run','reference_run','fit_run']:
        assert re.fullmatch(r'block-v1-[0-9]{8}-[0-9]{3}',value[name]),name
    assert value['reference_task_prefix']in ('reference-shard','reference-receive')
    return value
