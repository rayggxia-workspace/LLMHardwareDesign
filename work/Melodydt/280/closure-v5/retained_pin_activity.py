"""Alias observed RTL net bits to exact mapped cell pins (partial coverage).

Adapted from recurrent-step1/map_vcd_pins.py's graph-bit alias method. This
version deliberately accepts partial RTL activity and reports its coverage;
it must never be described as full gate replay. No event times are changed.
"""
import json
from pathlib import Path
from hashlib import sha256


def digest(path):
    h = sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''): h.update(chunk)
    return h.hexdigest()


def map_retained(raw, graph, output, top):
    raw, graph, output = map(Path, (raw, graph, output))
    design = json.loads(graph.read_text())['modules'][top]
    sources, codes, stack = {}, set(), []
    with raw.open() as f:
        for line in f:
            p = line.split()
            if not p: continue
            if p[0] == '$scope': stack.append(p[2])
            elif p[0] == '$upscope': stack.pop()
            elif p[0] == '$var' and stack == ['dut']:
                width, code, name = int(p[2]), p[3], p[4]
                codes.add(code)
                if name not in design['netnames']: continue
                bits = design['netnames'][name]['bits']
                assert len(bits) == width, (name, width, len(bits))
                for index, bit in enumerate(bits):
                    if isinstance(bit, int) and (bit not in sources or width == 1):
                        sources[bit] = (code, index, width)
            elif p[0] == '$enddefinitions': break
    for name, port in design['ports'].items():
        assert all(b in sources or b in ('0', '1') for b in port['bits']), name
    ids, scalar, derived = {}, set(), {}
    for bit, (code, index, width) in sources.items():
        if width == 1:
            ids[bit] = code; scalar.add(code)
        else:
            ident = 'retained_pin_' + str(bit)
            assert ident not in codes
            ids[bit] = ident
            derived.setdefault(code, []).append((index, ident, width))
    for bit in ('0', '1'):
        ids[bit] = 'retained_constant_' + bit
        assert ids[bit] not in codes
    annotations, total, unknown, observed_pins = 0, 0, 0, []
    with output.open('w') as out, raw.open() as inp:
        out.write('$timescale 1ps $end\n$scope module dut $end\n')
        for name, port in design['ports'].items():
            for index, bit in enumerate(port['bits']):
                suffix = '[%d]' % (index + port.get('offset', 0)) if len(port['bits']) > 1 else ''
                out.write('$var wire 1 %s %s%s $end\n' % (ids[bit], name, suffix))
                annotations += 1; total += 1; observed_pins.append(name+suffix)
        for name, cell in design['cells'].items():
            selected = []
            for pin, bits in cell['connections'].items():
                if not bits: continue
                assert len(bits) == 1
                total += 1
                bit = bits[0]
                if bit in ids: selected.append((pin, bit))
                elif bit in ('x', 'z'): unknown += 1
            if not selected: continue
            out.write('$scope module %s $end\n' % name)
            for pin, bit in selected:
                out.write('$var wire 1 %s %s $end\n' % (ids[bit], pin))
                annotations += 1; observed_pins.append(name+'/'+pin)
            out.write('$upscope $end\n')
        out.write('$upscope $end\n$enddefinitions $end\n')
        for line in inp:
            if '$enddefinitions' in line: break
        seen, last, first_time, end = set(), {}, None, None
        for line in inp:
            if line.startswith('#'):
                end = int(line[1:])
                if first_time is None: first_time = end; assert end == 0
                out.write(line)
                if end == 0:
                    for bit in ('0', '1'): out.write(bit + ids[bit] + '\n')
            else:
                p = line.split()
                if not p: continue
                if p[0][0] in 'bB' and len(p) == 2: value, code = p[0][1:], p[1]
                elif p[0][0] in '01xz': value, code = p[0][0], p[0][1:]
                else: continue
                if code not in scalar and code not in derived: continue
                assert set(value) <= {'0', '1'}
                if code in scalar:
                    assert len(value) == 1
                    out.write(value + code + '\n'); seen.add(code)
                if code in derived:
                    width = derived[code][0][2]; value = value.zfill(width)
                    assert len(value) == width
                    for index, ident, _ in derived[code]:
                        bit = value[-1-index]
                        if last.get(ident) != bit: out.write(bit+ident+'\n'); last[ident] = bit
        assert seen == scalar and len(last) == sum(len(v) for v in derived.values())
    return dict(expected_annotated_pins=annotations, total_connected_pins=total,
                pins_with_unobserved_activity=total-annotations, unknown_constant_pins=unknown,
                mapped_signal_bits=len(sources), scope='dut', final_timestamp_ps=end,
                observed_pin_set_sha256=sha256('\n'.join(sorted(observed_pins)).encode()).hexdigest(),
                raw_sha256=digest(raw), graph_sha256=digest(graph), pin_vcd_sha256=digest(output),
                method='Exact mapped connectivity aliases for retained RTL bits plus known constants; unobserved internal nets remain propagated estimates, not gate replay.')
