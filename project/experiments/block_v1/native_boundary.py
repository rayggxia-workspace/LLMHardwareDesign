"""Read-only acceptance of source-bound native input/constraint probes."""
import hashlib
import json
import re
from constraint_readback import audit


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root,out):
    config=json.loads((root/'project/experiments/block_v1/native_pipeline.json').read_text())
    source=out.parents[2]/config['floorplan_run']
    prep=out.parents[2]/config['preparation_run']/'tasks/native-prepare'
    bound=json.loads((prep/'receipt.json').read_text());assert bound['passed']is True
    budget=json.loads((root/'project/experiments/block_v1/physical-budget.json').read_text())
    results=[]
    for top in budget['leaves']:
        for policy in ['A','C']:
            folder=source/('tasks/native-floorplan-'+top+'-'+policy.lower())
            receipt=json.loads((folder/'receipt.json').read_text());assert receipt['passed']is True
            for name in ['native-floorplan-input.json','constraints-readback.sdc','prepare.log','prepared.odb']:
                assert sha(folder/name)==receipt['outputs'][name]
            assert 'capacitance 1fF' in(folder/'prepare.log').read_text()
            path=prep/(top+'-'+policy)/'pins.json'
            assert sha(path)==bound['outputs'][str(path.relative_to(prep))]
            pins=json.loads(path.read_text())['pins']
            text=(folder/'constraints-readback.sdc').read_text()
            checks=audit(text,pins,budget)
            for bad in [re.sub(r'(?m)^(set_load -pin_load )2\.0000 ',r'\g<1>0.0020 ',text),
                        re.sub(r'(?m)^set_input_delay[^\n]+\n','',text,count=1)]:
                assert bad!=text
                rejected=False
                try:audit(bad,pins,budget)
                except AssertionError:rejected=True
                assert rejected,'Boundary receiver accepted malformed constraints'
            results.append(dict(top=top,policy=policy,source=str(folder),receipt_sha256=sha(folder/'receipt.json'),
                checks=checks,wrong_load_and_missing_input_negative_rejected=True))
    (out/'native-boundary-audit.json').write_text(json.dumps(dict(schema='block-v1-native-boundary-audit/1',
        passed=True,candidates=results,scope='Exact current-source unplaced floorplan, pins, cells and full boundary constraints; complete physical quality remains unqualified'),indent=2)+'\n')
