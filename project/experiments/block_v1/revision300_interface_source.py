"""Explicit accepted escape selections; no retired V interface fallback."""
import json


def selected(root,out,kind):
    path=root/'project/experiments/block_v1/revision300-interface-sources.json'
    config=json.loads(path.read_text())
    assert config['schema']=='revision300-interface-sources/1'
    assert kind in config['escape'],('No current interface source selected',kind)
    base=out.parents[2];task=base/config['escape'][kind]
    assert base in task.resolve().parents and task.name=='revision300-escape-'+kind
    return task
