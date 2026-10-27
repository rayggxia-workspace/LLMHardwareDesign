"""Exact coordinate controls using receipt-bound original native pin exports."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from pin_contract import inspect, observed, rectangles, script


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exercise(plan, text, actual):
    positive = inspect(plan,text,actual)
    assert positive['passed']
    rows = observed(actual)
    names = sorted(rows)
    assert len(names) >= 2

    def serialize(values):
        return ''.join(name+'\t'+layer+'\t'+'\t'.join(map(str,box))+'\n'
                       for name,(layer,box) in values.items())

    def rejected(p,t,a):
        try:
            return not inspect(p,t,a)['passed']
        except (AssertionError,ValueError):
            return True

    faults = {}
    altered = copy.deepcopy(rows)
    altered[names[0]][1][0] += 1
    altered[names[0]][1][2] += 1
    faults['native_rectangle_translated_one_dbu'] = rejected(plan,text,serialize(altered))
    altered = copy.deepcopy(rows)
    altered[names[0]][1][2] += 1
    faults['native_rectangle_width_one_dbu'] = rejected(plan,text,serialize(altered))
    altered = copy.deepcopy(rows)
    altered[names[0]],altered[names[1]] = altered[names[1]],altered[names[0]]
    faults['swapped_bit_rectangles'] = rejected(plan,text,serialize(altered))
    altered = copy.deepcopy(rows)
    altered[names[0]] = ('metal9',altered[names[0]][1])
    faults['wrong_layer'] = rejected(plan,text,serialize(altered))
    altered = copy.deepcopy(rows)
    del altered[names[0]]
    faults['missing_pin'] = rejected(plan,text,serialize(altered))
    faults['duplicate_pin'] = rejected(plan,text,actual+actual.splitlines()[0]+'\n')
    faults['altered_placement_script'] = rejected(plan,text.replace('-pin_size {.8 .8}','-pin_size {.81 .8}',1),actual)
    altered_plan = copy.deepcopy(plan)
    altered_plan['pins'][0]['xy_um'][0] += .8
    faults['altered_original_plan'] = rejected(altered_plan,text,actual)
    assert all(faults.values())
    precise = script(plan)
    precise_expected, precise_proof = rectangles(plan,precise)
    assert inspect(plan,precise,serialize(precise_expected))['passed']
    assert precise_proof['preformat_plan_changed_count'] == 0
    result = dict(passed=True,positive=positive,negative_controls=faults,
                  precise_serialization_preserves_original_coordinates=True,
                  comparator_sha256=sha(Path(__file__).with_name('pin_contract.py')),
                  scope='Software comparator controls on original native-export TSV, bound to source and receiver receipts. No ODB editing, new STA/DRC qualification, or tolerance; fresh complete physical reception still required.')
    return result


def controls(source, received, out):
    out.mkdir(parents=True, exist_ok=False)
    source_receipt = json.loads((source/'receipt.json').read_text())
    actual_receipt = json.loads((received/'receipt.json').read_text())
    assert source_receipt['passed'] is True
    for name in ['pins.json','pins.tcl']:
        assert sha(source/name) == source_receipt['outputs'][name]
    assert sha(received/'physical-pins.tsv') == actual_receipt['outputs']['physical-pins.tsv']
    result = exercise(json.loads((source/'pins.json').read_text()),
                      (source/'pins.tcl').read_text(),(received/'physical-pins.tsv').read_text())
    result['inputs']={str(p):dict(sha256=sha(p),bytes=p.stat().st_size) for p in
                     [source/'receipt.json',source/'pins.json',source/'pins.tcl',received/'receipt.json',received/'physical-pins.tsv']}
    (out/'pin-contract-controls.json').write_text(json.dumps(result,indent=2)+'\n')
    positive=result['positive'];faults=result['negative_controls']
    print(json.dumps(dict(passed=True,signal_pins=positive['actual_signal_pins'],
                         serialization_changed=positive['preformat_plan_changed_count'],
                         rejected_faults=faults,scope=result['scope']),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('received',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    controls(args.source,args.received,args.output)
