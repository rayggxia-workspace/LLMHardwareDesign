"""Replay a real LEF fixture and reject meaningful geometry/pin corruptions."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from assemble_eco_views import check_refined_lef


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fixture', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--layer', choices=['metal3','metal4'], default='metal4')
    a = ap.parse_args()
    assert not a.out.exists()
    names = ['s_sram_256x128_freepdk45.lef', 'bank.lef', 'receipt.json', 'native-m'+a.layer[-1]+'.tsv']
    source, refined, proof, native = [a.fixture / n for n in names]
    s, t = source.read_text(), refined.read_text()
    r = json.loads(proof.read_text())
    boxes = [tuple(map(int, line.split())) for line in native.read_text().splitlines()]
    positive = check_refined_lef(s, t, r, boxes, a.layer)
    cases = dict(pin_change=t.replace('PIN ', 'PIN corrupt_', 1))
    cases['size_change'] = re.sub(r'\bSIZE\s+([0-9.]+)',
        lambda m: 'SIZE ' + format(float(m.group(1)) + .005, '.4f'), t, count=1)
    m = re.search(r'(?s)\bOBS\b.*?\bRECT\s+([-\d.]+)', t)
    assert m
    cases['other_obs_change'] = t[:m.start(1)] + format(float(m.group(1)) + .005, '.4f') + t[m.end(1):]
    m = re.search(r'(?s)\bOBS\b.*?LAYER\s+'+a.layer+r'\s*;\s*(RECT\s+([-\d.]+))', t)
    assert m
    cases['declared_layer_coordinate_change'] = t[:m.start(2)] + format(float(m.group(2)) + .005, '.4f') + t[m.end(2):]
    cases['non_rect_layer_injection'] = t[:m.start()] + 'LAYER metal5 ;\n' + t[m.start():]
    controls = [(name, text, r, boxes) for name, text in cases.items()]
    changed_boxes = boxes[:]
    first = changed_boxes[0]
    changed_boxes[0] = (first[0] + 1, *first[1:])
    controls.append(('native_geometry_change', t, r, changed_boxes))
    changed_proof = dict(r, unchanged_prefix_sha256='0' * 64)
    controls.append(('bad_producer_boundary_digest', t, changed_proof, boxes))
    rejected = {}
    for name, text, p, b in controls:
        assert text != t or p != r or b != boxes
        try:
            check_refined_lef(s, text, p, b, a.layer)
        except (AssertionError, ValueError):
            rejected[name] = True
        else:
            raise AssertionError(name + ' was accepted')
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    result = dict(passed=positive['passed'] and all(rejected.values()),
        scope='Actual LEF fixture and seven corruptions; no physical qualification',
        positive=positive, negative_controls=rejected,
        inputs={p.name: sha(p) for p in [source, refined, proof, native]},
        validator_sha256=sha(Path(__file__).with_name('assemble_eco_views.py')))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
