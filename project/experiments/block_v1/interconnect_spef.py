"""Join unchanged native macro RC graphs and explicit candidate link segments.

This accepts the pinned OpenRCX SPEF grammar only. Native cell connections,
ground/coupling capacitors and resistors are retained; native boundary ports
become internal parasitic nodes. Unconnected ports remain external ports.
It does not perform placement, routing, extraction or crosstalk signoff.
"""
from collections import defaultdict
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import shutil

EXTRA_MAP = 100_000_000
EXTRA_ROW = 1_000_000_000
INTERNAL_NODE = 99_000_000
MAP_REF = re.compile(r'\*(\d+)(?=:|$)')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def plain(name):
    return re.sub(r'\\(.)', r'\1', name)


class Records:
    """Order-independent record fingerprint retaining duplicates and values."""
    def __init__(self):
        self.counts = defaultdict(int)
        self.total = 0
        self.xor = 0

    def add(self, kind, tokens):
        self.counts[kind] += 1
        value = int.from_bytes(hashlib.sha256(
            (kind + '\t' + '\t'.join(tokens)).encode()).digest(), 'big')
        self.total = (self.total + value) % (1 << 256)
        self.xor ^= value

    def result(self):
        return dict(counts=dict(self.counts), sum256=f'{self.total:064x}',
                    xor256=f'{self.xor:064x}')


def blocks(path):
    current = None
    with Path(path).open() as stream:
        for line in stream:
            t = line.split()
            if not t:
                continue
            if t[0] == '*D_NET':
                assert current is None and len(t) == 3
                current = [t]
            elif current is not None:
                current.append(t)
                if t[0] == '*END':
                    yield current
                    current = None
    assert current is None


def inventory(path, prefix, offset):
    names = {}
    ports = {}
    header = {}
    with Path(path).open() as stream:
        for line in stream:
            t = line.split()
            if not t:
                continue
            if t[0] == '*D_NET':
                break
            if len(t) == 2 and re.fullmatch(r'\*\d+', t[0]):
                names[int(t[0][1:])] = t[1]
            elif t[0] in ('*C_UNIT', '*R_UNIT', '*DIVIDER', '*DELIMITER', '*BUS_DELIMITER'):
                header[t[0]] = t[1:]
    assert header == {'*DIVIDER': ['/'], '*DELIMITER': [':'],
                      '*BUS_DELIMITER': ['[]'], '*C_UNIT': ['1', 'PF'],
                      '*R_UNIT': ['1', 'OHM']}, header
    assert names and max(names) < 10_000_000
    # A top port can appear as a coupling node in other nets; enumerate all
    # port identities before transforming any native RC record.
    net = None
    in_conn = False
    with Path(path).open() as stream:
        for line in stream:
            t = line.split()
            if not t:
                continue
            if t[0] == '*D_NET':
                net = int(t[1][1:])
                in_conn = False
            elif t[0] == '*CONN':
                in_conn = True
            elif t[0] in ('*CAP', '*RES', '*END'):
                in_conn = False
            elif in_conn and t[0] == '*P':
                name = plain(t[1])
                assert name not in ports and plain(names[net]) == name
                ports[name] = dict(net=net, literal=t[1], direction=t[2])
    assert ports and 'clk' in ports
    return dict(path=str(path), prefix=prefix, offset=offset, names=names,
                ports=ports, port_literals={v['literal']: k for k, v in ports.items()},
                sha256=sha(path))


def paired_links(left, right):
    if (left, right) == ('m', 't'):
        data = ('rsp_data', 'write_data')
        valid = ('rsp_valid', 'write_valid')
        ready = ('write_ready', 'rsp_ready')
    elif (left, right) == ('t', 's'):
        data = ('read_data', 'din')
        valid = ('read_valid', 'req')
        ready = ('ready', 'read_take')
    else:
        raise ValueError((left, right))
    result = [dict(id=f'f{i:03}', source=['left', f'{data[0]}[{i}]'],
                   sink=['right', f'{data[1]}[{i}]'], role='data', bit=i)
              for i in range(128)]
    result += [dict(id='f128', source=['left', valid[0]],
                    sink=['right', valid[1]], role='valid'),
               dict(id='r000', source=['right', ready[0]],
                    sink=['left', ready[1]], role='ready')]
    return result


def selection(inventories, links):
    chosen = {(side, port) for link in links
              for side, port in (link['source'], link['sink'])}
    assert len(chosen) == 2 * len(links)
    for link in links:
        for field, direction in [('source', 'O'), ('sink', 'I')]:
            side, port = link[field]
            assert inventories[side]['ports'][port]['direction'] == direction
    return chosen | {(side, 'clk') for side in inventories}


def node(token, inv, selected):
    port_by_literal = inv['port_literals']
    if token in port_by_literal:
        port = port_by_literal[token]
        if (inv['prefix'], port) in selected:
            return f"*{inv['offset'] + inv['ports'][port]['net']}:{inv['offset'] * 10 + INTERNAL_NODE}"
        return inv['prefix'] + '_' + token
    if re.match(r'^\*\d+', token):
        # OpenROAD flattens hierarchical boundary nets. Both halves of a
        # joined net therefore use the same logical name; their native node
        # suffixes must stay distinct, including all cross-net CC references.
        internal = re.fullmatch(r'\*(\d+):(\d+)', token)
        port_nets = inv.get('port_nets')
        if port_nets is None:
            port_nets = inv['port_nets'] = {v['net'] for v in inv['ports'].values()}
        if internal and int(internal[1]) in port_nets:
            assert int(internal[2]) < INTERNAL_NODE
            return f"*{inv['offset'] + int(internal[1])}:{inv['offset'] * 10 + int(internal[2])}"
        return MAP_REF.sub(lambda m: '*' + str(inv['offset'] + int(m[1])), token)
    raise AssertionError(('Unsupported native node', token))


def transform(block, inv, selected, records):
    name = inv['names'][int(block[0][1][1:])]
    net_port = plain(name) if plain(name) in inv['ports'] else None
    out = dict(native_cap=block[0][2], conn=[], cap=[], res=[],
               native_net='*' + str(inv['offset'] + int(block[0][1][1:])),
               port=net_port, prefix=inv['prefix'])
    if net_port:
        out['internal_node'] = node(inv['ports'][net_port]['literal'], inv, selected)
    mode = None
    for t in block[1:]:
        if t[0] in ('*CONN', '*CAP', '*RES', '*END'):
            mode = {'*CONN': 'conn', '*CAP': 'cap', '*RES': 'res', '*END': None}[t[0]]
            continue
        if mode == 'conn':
            assert t[0] in ('*P', '*I')
            if t[0] == '*P':
                if (inv['prefix'], plain(t[1])) in selected:
                    continue
                row = ['*P', inv['prefix'] + '_' + t[1], *t[2:]]
            else:
                row = ['*I', node(t[1], inv, selected), *t[2:]]
                records.add('conn', row[1:])
            out['conn'].append(row)
        elif mode in ('cap', 'res'):
            assert t[0].isdigit() and len(t) in (3, 4)
            if mode == 'res':
                assert len(t) == 4
            row = [node(v, inv, selected) for v in t[1:-1]] + [t[-1]]
            records.add(mode, row)
            out[mode].append(row)
        else:
            raise AssertionError(t)
    assert out['cap'] and out['res']
    return out


def header(names, ports=()):
    text = '''*SPEF "ieee 1481-1999"
*DESIGN "interconnect_fixture"
*DATE "immutable research inputs"
*VENDOR "LLMHardwareDesign"
*PROGRAM "native graph join with explicit link pi RC"
*VERSION "1"
*DESIGN_FLOW "NAME_SCOPE LOCAL" "PIN_CAP NONE"
*DIVIDER /
*DELIMITER :
*BUS_DELIMITER []
*T_UNIT 1 NS
*C_UNIT 1 PF
*R_UNIT 1 OHM
*L_UNIT 1 HENRY
*NAME_MAP
'''
    text += ''.join(f'*{k} {v}\n' for k, v in sorted(names.items()))
    if ports:
        text += '*PORTS\n' + ''.join(f'{p} {d}\n' for p, d in ports)
    return text + '\n'


def write_net(stream, name, pieces, connections=(), capacitors=(), resistors=()):
    total = sum((Decimal(p['native_cap']) for p in pieces), Decimal(0))
    # Added capacitors here are grounded pi halves only.
    total += sum((Decimal(row[-1]) for row in capacitors), Decimal(0))
    stream.write(f'*D_NET {name} {total}\n*CONN\n')
    for row in [row for p in pieces for row in p['conn']] + list(connections):
        stream.write(' '.join(row) + '\n')
    stream.write('*CAP\n')
    for i, row in enumerate((row for p in pieces for row in p['cap']), 1):
        stream.write(str(i) + ' ' + ' '.join(row) + '\n')
    for i, row in enumerate(capacitors, EXTRA_ROW):
        stream.write(str(i) + ' ' + ' '.join(map(str, row)) + '\n')
    stream.write('*RES\n')
    for i, row in enumerate((row for p in pieces for row in p['res']), 1):
        stream.write(str(i) + ' ' + ' '.join(row) + '\n')
    for i, row in enumerate(resistors, EXTRA_ROW):
        stream.write(str(i) + ' ' + ' '.join(map(str, row)) + '\n')
    stream.write('*END\n\n')


def prepare(native, destination, links):
    destination = Path(destination)
    destination.mkdir(exist_ok=True)
    inventories = {side: inventory(row['spef'], side, i * 10_000_000)
                   for i, (side, row) in enumerate(native.items(), 1)}
    chosen = selection(inventories, links)
    names = {inv['offset'] + k: 'u_' + inv['prefix'] + '/' + v
             for inv in inventories.values() for k, v in inv['names'].items()}
    names[EXTRA_MAP] = 'clk'
    ports = [('clk', 'I')]
    for side, inv in inventories.items():
        ports += [(side + '_' + p['literal'], p['direction'])
                  for name, p in inv['ports'].items() if (side, name) not in chosen]
    record = Records()
    selected_blocks = {}
    common = destination / 'common-body.spef'
    with common.open('w') as stream:
        for side, inv in inventories.items():
            for block in blocks(inv['path']):
                piece = transform(block, inv, chosen, record)
                if (side, piece['port']) in chosen:
                    selected_blocks[side + ':' + piece['port']] = piece
                else:
                    write_net(stream, piece['native_net'], [piece])
        clocks = [selected_blocks.pop(side + ':clk') for side in inventories]
        roots = [p['internal_node'] for p in clocks]
        write_net(stream, '*' + str(EXTRA_MAP), clocks,
                  connections=[['*P', 'clk', 'I']],
                  resistors=[['clk', root, '0.000001'] for root in roots])
    # Store native maps and selected physical graphs once, not a copy of all
    # native parasitics for every length/driver condition.
    saved_inv = {side: {k: v for k, v in inv.items() if k not in ('names', 'port_nets')}
                 for side, inv in inventories.items()}
    metadata = dict(schema='finite-native-interconnect-preparation/1',
                    inventories=saved_inv, maps=names,
                    selected=selected_blocks, links=links,
                    expected_native_records=record.result(),
                    common_sha256={},
                    shared_clock='Shared ideal root, both original native CTS graphs retained; no common CTS signoff',
                    manufacturing_qualified=False)
    # Three immutable headers resolve boundary aliases to actual flattened
    # top nets. Bodies contain exactly the same native records. Files are
    # shared by all length/RC conditions of their topology.
    for topology in ('direct', 'endpoints', 'relay'):
        target = destination / ('common-' + topology + '.spef')
        with target.open('w') as stream, common.open() as body:
            stream.write(header(canonical_maps(metadata, topology), ports))
            shutil.copyfileobj(body, stream, length=1024 * 1024)
        metadata['common_sha256'][topology] = sha(target)
    (destination / 'prepared.json').write_text(json.dumps(metadata) + '\n')
    return metadata


def canonical_maps(meta, topology):
    names = {int(k): v for k, v in meta['maps'].items()}
    endpoints = {}
    for link in meta['links']:
        endpoints[tuple(link['source'])] = link['id'] + ('_src' if topology != 'direct' else '')
        endpoints[tuple(link['sink'])] = link['id'] + ('_dst' if topology != 'direct' else '')
    for side, inv in meta['inventories'].items():
        for port, row in inv['ports'].items():
            if port == 'clk':
                name = 'clk'
            else:
                name = endpoints.get((side, port), side + '_' + row['literal'])
            names[inv['offset'] + row['net']] = name
    return names


def cell_pin(token, maps):
    match = re.fullmatch(r'\*(\d+):(.+)', token)
    assert match
    return plain(maps[int(match[1])]) + '/' + plain(match[2])


def verilog_identifier(name):
    assert not any(c.isspace() for c in name)
    return '\\' + name + ' '


def wrapper(meta, native, topology, cell='BUF_X4'):
    assert topology in ('direct', 'endpoints', 'relay')
    cells = {key:cell for key in ('tx','rx','mid')} if isinstance(cell,str) else cell
    assert set(cells)=={'tx','rx','mid'}
    assert all(v in ('BUF_X1','BUF_X2','BUF_X4','BUF_X8') for v in cells.values())
    wires = set()
    endpoint = {}
    instances = []
    for link in meta['links']:
        key = link['id']
        if topology == 'direct':
            endpoint[tuple(link['source'])] = endpoint[tuple(link['sink'])] = key
            wires.add(key)
        else:
            endpoint[tuple(link['source'])] = key + '_src'
            endpoint[tuple(link['sink'])] = key + '_dst'
            wires.update([key + '_src', key + '_dst', key + '_seg0'])
            last = key + '_seg0'
            instances.append(f'{cells["tx"]} ic_{key}_tx (.A({key}_src), .Z({last}));')
            if topology == 'relay':
                wires.add(key + '_seg1')
                instances.append(f'{cells["mid"]} ic_{key}_mid (.A({last}), .Z({key}_seg1));')
                last = key + '_seg1'
            instances.append(f'{cells["rx"]} ic_{key}_rx (.A({last}), .Z({key}_dst));')
    ports = [('clk', 'input')]
    calls = []
    for side, inv in meta['inventories'].items():
        groups = defaultdict(dict)
        for port, detail in inv['ports'].items():
            if port == 'clk':
                value = 'clk'
            elif (side, port) in endpoint:
                value = endpoint[side, port]
            else:
                name = side + '_' + port
                assert re.fullmatch(r'[A-Za-z_]\w*(?:\[\d+\])?', name)
                value = name
                ports.append((name, 'input' if detail['direction'] == 'I' else 'output'))
            match = re.fullmatch(r'(.+)\[(\d+)\]', port)
            if match:
                groups[match[1]][int(match[2])] = value
            else:
                groups[port][None] = value
        conns = []
        for port, bits in groups.items():
            if None in bits:
                assert len(bits) == 1
                value = bits[None]
            else:
                assert set(bits) == set(range(max(bits) + 1))
                value = '{' + ', '.join(bits[i] for i in sorted(bits, reverse=True)) + '}'
            conns.append('.' + port + '(' + value + ')')
        calls.append(native[side]['top'] + ' u_' + side + ' (' + ', '.join(conns) + ');')
    # True vector ports, not escaped scalar identifiers containing brackets:
    # OpenROAD distinguishes foo[0] from the escaped scalar foo\[0\].
    top_groups = {}
    for port, direction in ports:
        match = re.fullmatch(r'(.+)\[(\d+)\]', port)
        name = match[1] if match else port
        bit = int(match[2]) if match else None
        entry = top_groups.setdefault(name, dict(direction=direction, bits=set()))
        assert entry['direction'] == direction
        entry['bits'].add(bit)
    result = 'module interconnect_fixture (' + ', '.join(top_groups) + ');\n'
    for name, row in top_groups.items():
        bits = row['bits']
        if bits == {None}:
            dimensions = ''
        else:
            assert None not in bits and bits == set(range(max(bits)+1))
            dimensions = '[' + str(max(bits)) + ':0] '
        result += row['direction'] + ' ' + dimensions + name + ';\n'
    result += ''.join('wire ' + n + ';\n' for n in sorted(wires))
    return result + '\n'.join(calls + instances) + '\nendmodule\n'


def link_spef(meta, destination, topology, length_um, factor=1., cell='BUF_X4',
              c_per_um_ff=0.15539099611464, r_per_um_ohm=0.015,
              resistance_multiplier=1., capacitance_multiplier=1.):
    lengths = length_um if isinstance(length_um,dict) else {r['id']:length_um for r in meta['links']}
    assert set(lengths)=={r['id']for r in meta['links']}
    assert all(v>0 for v in lengths.values()) and factor > 0 and topology in ('direct', 'endpoints', 'relay')
    cells = {key:cell for key in ('tx','rx','mid')} if isinstance(cell,str) else cell
    assert set(cells)=={'tx','rx','mid'}
    assert all(v in ('BUF_X1','BUF_X2','BUF_X4','BUF_X8') for v in cells.values())
    maps = canonical_maps(meta, topology)
    rows = []
    measurements = []
    next_map = EXTRA_MAP + 1

    def mapped(name):
        nonlocal next_map
        i = next_map
        maps[i] = name
        next_map += 1
        return '*' + str(i)

    def segment(name, a, b, distance, pieces=(), conn=()):
        net = mapped(name)
        cap = Decimal(str(distance * c_per_um_ff * factor * capacitance_multiplier / 1000))
        # Explicit two via10 endpoints plus one possible via11 turn. This is
        # a declared cost budget, not a geometry/placement feasibility claim.
        resistance = Decimal(str((distance * r_per_um_ohm + .24) * factor * resistance_multiplier))
        caps = [[a, str(cap / 2)], [b, str(cap / 2)]]
        resistors = [[a, b, str(resistance)]]
        rows.append((net, pieces, conn, caps, resistors))
        return dict(net=name, length_um=distance, wire_cap_ff=float(cap * 1000),
                    series_r_ohm=float(resistance))

    for link in meta['links']:
        source = meta['selected'][':'.join(link['source'])]
        sink = meta['selected'][':'.join(link['sink'])]
        source_node = source['internal_node']
        sink_node = sink['internal_node']
        drivers = [r[1] for r in source['conn'] if r[0] == '*I' and r[2] == 'O']
        sinks = [r[1] for r in sink['conn'] if r[0] == '*I' and r[2] == 'I']
        assert len(drivers) == 1 and sinks
        key = link['id']
        distance=lengths[key]
        costs = []
        if topology == 'direct':
            costs.append(segment(key, source_node, sink_node, distance, [source, sink]))
        else:
            tx, rx = mapped('ic_' + key + '_tx'), mapped('ic_' + key + '_rx')
            costs.append(segment(key + '_src', source_node, tx + ':A', 8., [source],
                                 [['*I', tx + ':A', 'I', '*D', cells['tx']]]))
            costs.append(segment(key + '_dst', rx + ':Z', sink_node, 8., [sink],
                                 [['*I', rx + ':Z', 'O', '*D', cells['rx']]]))
            if topology == 'endpoints':
                costs.append(segment(key + '_seg0', tx + ':Z', rx + ':A', distance,
                                     conn=[['*I', tx + ':Z', 'O', '*D', cells['tx']],
                                           ['*I', rx + ':A', 'I', '*D', cells['rx']]]))
            else:
                mid = mapped('ic_' + key + '_mid')
                for index, a, b in [(0, tx + ':Z', mid + ':A'), (1, mid + ':Z', rx + ':A')]:
                    acell=cells['tx'] if index==0 else cells['mid']
                    bcell=cells['mid'] if index==0 else cells['rx']
                    costs.append(segment(key + '_seg' + str(index), a, b, distance / 2,
                                         conn=[['*I', a, 'O', '*D', acell], ['*I', b, 'I', '*D', bcell]]))
        measurements.append(dict(**link, source_driver=cell_pin(drivers[0], maps),
                                 first_native_loads=[cell_pin(p, maps) for p in sinks], costs=costs))
    # Keep native name IDs so coupling references from common.spef resolve to
    # exactly the same native internal nodes under every topology.
    with Path(destination).open('w') as stream:
        stream.write(header(maps))
        for row in rows:
            write_net(stream, *row)
    return dict(links=measurements, buffer_cell=cell,
                added_buffer_count=len(meta['links']) * dict(direct=0, endpoints=2, relay=3)[topology],
                main_length_um=length_um, rc_factor=factor, local_segment_um=8,
                new_layer_coupling_qualified=False, physical_implementation_completed=False)


def audit_native(meta, common, links):
    actual = Records()
    for path in [common, links]:
        for block in blocks(path):
            mode = None
            for row in block[1:]:
                if row[0] in ('*CONN', '*CAP', '*RES', '*END'):
                    mode = {'*CONN': 'conn', '*CAP': 'cap', '*RES': 'res', '*END': None}[row[0]]
                elif mode == 'conn' and row[0] == '*I':
                    cell = re.fullmatch(r'\*(\d+):(.+)', row[1])
                    assert cell
                    if int(cell[1]) < EXTRA_MAP:
                        actual.add('conn', row[1:])
                elif mode in ('cap', 'res') and int(row[0]) < EXTRA_ROW:
                    actual.add(mode, row[1:])
    observed = actual.result()
    assert observed == meta['expected_native_records'], ('Native record altered/lost', observed, meta['expected_native_records'])
    return dict(passed=True, native_connections_ground_and_coupling_caps_resistors_preserved=True,
                records=observed)
