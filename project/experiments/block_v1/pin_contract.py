"""Exact M10 rectangles declared by the receipt-bound placement script.

Legacy %g serialization has six significant digits. The pre-serialization
JSON is retained as provenance, but cannot describe the executed coordinates
when formatting changes a value. No tolerance or observed-coordinate fitting.
"""
from decimal import Decimal
import hashlib
import json
import re


def script(plan, legacy=False):
    text = 'set planned_pins [dict create]\n'
    names = set()
    for pin in plan['pins']:
        name = pin['pin']
        assert name not in names and not any(c in name for c in '{}\\\n\r')
        names.add(name)
        assert pin['layer'] == 'metal10' and pin['size_um'] in ([.8,.8],[2.,2.])
        size=' '.join(str(Decimal(str(value))) for value in pin['size_um'])
        if pin['size_um']==[.8,.8]:size='.8 .8'
        xy = [('%g' % value if legacy else str(Decimal(str(value)))) for value in pin['xy_um']]
        assert all(Decimal(value).is_finite() for value in xy)
        text += 'dict set planned_pins {' + name + '} 1\n'
        text += 'place_pin -pin_name {' + name + '} -layer metal10 -location {' + ' '.join(xy) + '} -pin_size {'+size+'}\n'
    text += 'set actual_pins {}\nforeach p [[ord::get_db_block] getBTerms] {if {[$p getSigType] ni {POWER GROUND}} {lappend actual_pins [$p getName]}}\n'
    text += 'if {[lsort $actual_pins] ne [lsort [dict keys $planned_pins]]} {error "Exact macro pin inventory mismatch"}\n'
    return text


def rectangles(plan, executed_script, dbu=2000):
    assert dbu == 2000
    precise = script(plan)
    legacy = script(plan, legacy=True)
    assert executed_script in (precise, legacy), 'Placement script differs from exact supported generator'
    serializer = 'exact-decimal' if executed_script == precise else 'legacy-six-significant-digit-g'
    expected = {}
    changed = []
    pattern = r'^place_pin -pin_name \{([^}]+)\} -layer metal10 -location \{([^ ]+) ([^}]+)\} -pin_size \{([^ ]+) ([^}]+)\}$'
    locations = {p['pin']: p for p in plan['pins']}
    for line in executed_script.splitlines():
        if not line.startswith('place_pin '):
            continue
        match = re.fullmatch(pattern, line)
        assert match, line
        name, x, y, sx, sy = match.groups()
        assert [Decimal(sx),Decimal(sy)]==[Decimal(str(v))for v in locations[name]['size_um']]
        box = [(Decimal(value) + delta) * dbu for value, delta in
               [(x, -Decimal(sx)/2), (y, -Decimal(sy)/2), (x, Decimal(sx)/2), (y, Decimal(sy)/2)]]
        assert all(value == value.to_integral_value() for value in box), 'Fractional DBU in executed pin'
        expected[name] = ('metal10', [int(value) for value in box])
        requested = locations[name]['xy_um']
        if [Decimal(x), Decimal(y)] != [Decimal(str(v)) for v in requested]:
            changed.append(dict(pin=name,preformat_xy_um=requested,executed_xy_um=[str(Decimal(x)), str(Decimal(y))]))
    assert set(expected) == set(locations)
    proof = dict(serializer=serializer, declared_signal_pins=len(expected),
                 exact_script_sha256=hashlib.sha256(executed_script.encode()).hexdigest(),
                 preformat_plan_changed_count=len(changed), serialization_changes=changed,
                 expected_rectangles_sha256=hashlib.sha256(json.dumps(expected, sort_keys=True).encode()).hexdigest(),
                 scope='Expected rectangles derive only from complete receipt-bound placement script and its original JSON; exact native DBU comparison, no tolerance and no fitting to ODB observations.')
    return expected, proof


def observed(text):
    result = {}
    for line in text.splitlines():
        name, layer, *box = line.split('\t')
        assert name not in result and len(box) == 4
        result[name] = (layer, [int(value) for value in box])
    return result


def inspect(plan, executed_script, actual, dbu=2000):
    expected, proof = rectangles(plan, executed_script, dbu)
    got = observed(actual)
    proof.update(passed=expected == got, exact_inventory=set(expected) == set(got),
                 actual_signal_pins=len(got), mismatch=[name for name in expected if got.get(name) != expected[name]])
    return proof
