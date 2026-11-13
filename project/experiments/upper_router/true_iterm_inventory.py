"""Prove directed native ITerm access and bind a source-owned open cut.

Run inside KLayout in batch mode. The input names the OpenROAD executable,
source-bound configuration, and an output directory through environment
variables. Native metal connectivity is checked before emitting contracts.
"""
from collections import defaultdict, deque
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from adapter import bind_request
from geometry import validate
from native_inventory import contains, file_hash, read_json
from route_contract import VERSION, elaborate, expand, require

SCHEMA = 'native-iterm-cut-source/1'
VIEWS = ('odb', 'def', 'netlist', 'gds')
M10 = 'metal10'
RECT = re.compile(r'\bmetal(\d+) \(\s*(-?\d+) +(-?\d+)\s*\) RECT \(\s*(-?\d+) +(-?\d+) +(-?\d+) +(-?\d+)\s*\)')
NET = re.compile(r'^\s*-\s+(\S+)\s+')
LAYER = re.compile(r'(metal|via)([1-9]\d*)\Z')
DIRECTIONS = {'driver': 'OUTPUT', 'sink': 'INPUT'}


@dataclass
class Terminal:
    name: str
    pin: str
    master: str
    master_type: str
    direction: str
    net: str
    signal: str
    status: str
    orient: str
    x: int
    y: int
    members: list = field(default_factory=list)
    aliases: list = field(default_factory=list)
    shapes: list = field(default_factory=list)

    @property
    def key(self):
        return f'{self.name}/{self.pin}'


def bound_file(record):
    path = Path(record['path']).resolve()
    require(path.is_file() and file_hash(path) == record['sha256'], f'source fingerprint differs: {path}')
    return path


def parse_export(path):
    block = None
    terms = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        fields = line.split('\t')
        if fields[0] == 'BLOCK':
            require(block is None and len(fields) == 7, 'duplicate or malformed ODB block identity')
            block = (fields[1], *(int(v) for v in fields[2:]))
        elif fields[0] == 'ENDPOINT':
            term = Terminal(*fields[1:-2], *(int(v) for v in fields[-2:]))
            require(term.key not in terms, f'duplicate ODB ITerm: {term.key}')
            terms[term.key] = term
        elif fields[0] in ('MEMBER', 'ALIAS'):
            term = terms[f'{fields[1]}/{fields[2]}']
            if fields[0] == 'MEMBER':
                term.members.append(tuple(fields[3:]))
            else:
                term.aliases.append(fields[3])
        elif len(fields) == 7 and fields[0] in terms:
            terms[fields[0]].shapes.append((fields[1], fields[2], tuple(int(v) for v in fields[3:])))
    require(block is not None and terms, 'missing exact native ODB export')
    return block, terms


def net_patches(path, nets):
    result = defaultdict(list)
    active = False
    current = None
    with path.open(encoding='utf-8') as source:
        for line in source:
            if line.startswith('NETS '):
                active = True
                continue
            if line.startswith('END NETS'):
                break
            if not active:
                continue
            match = NET.match(line)
            if match:
                current = match[1]
            if current not in nets:
                continue
            for layer, x, y, *offsets in RECT.findall(line):
                x, y, a, b, c, d = map(int, (x, y, *offsets))
                result[current].append((f'metal{layer}', 'def-rect', (x+a, y+b, x+c, y+d)))
    return result


def intersects(a, b, area=False):
    x = min(a[2], b[2]) - max(a[0], b[0])
    y = min(a[3], b[3]) - max(a[1], b[1])
    return min(x, y) > 0 if area else min(x, y) >= 0


def on_layer(shapes, layer, rect):
    return any(l == layer and intersects(r, rect, area=True) for l, _, r in shapes)


def covered(rect, copper):
    """Return whether the union of DBU rectangles covers the whole window."""
    x0, y0, x1, y1 = rect
    relevant = [r for r in copper if intersects(rect, r, area=True)]
    edges = sorted({x0, x1, *(max(x0, r[0]) for r in relevant), *(min(x1, r[2]) for r in relevant)})
    for a, b in zip(edges, edges[1:]):
        end = y0
        for lo, hi in sorted((r[1], r[3]) for r in relevant if r[0] <= a and r[2] >= b):
            if lo > end:
                break
            end = max(end,hi)
        if end < y1:
            return False
    return True


def connected_native_access(term, patches):
    """Follow physical same-net metal and cuts, ending at the exact ITerm."""
    wires = [s for s in term.shapes if s[1] in ('wire', 'wire-via')] + patches
    pins = [s for s in term.shapes if s[1].startswith('iterm-pin')]
    require(wires and pins, f'native route/ITerm geometry absent: {term.key}')
    levels = defaultdict(list)
    for i, (layer, _, rect) in enumerate(wires):
        match = LAYER.fullmatch(layer)
        require(match and int(match[2]) <= (10 if match[1] == 'metal' else 9),
                f'non-native routed layer on open leg: {term.key} {layer}')
        levels[layer].append(i)
    goals = {i for i, (layer, _, rect) in enumerate(wires) if on_layer(pins, layer, rect)}
    queue = deque(goals)
    reached = set(goals)
    while queue:
        index = queue.popleft()
        layer, _, rect = wires[index]
        kind, n = LAYER.fullmatch(layer).groups()
        n = int(n)
        adjacent = ([layer, f'via{n-1}', f'via{n}'] if kind == 'metal'
                    else [f'metal{n}', f'metal{n+1}'])
        for next_layer in adjacent:
            for other in levels[next_layer]:
                if other not in reached and intersects(rect, wires[other][2], area=next_layer != layer):
                    reached.add(other)
                    queue.append(other)
    require(any(i in reached for i in levels[M10]), f'no native copper path to exact ITerm: {term.key}')
    return [wire for i, wire in enumerate(wires) if i in reached]


def require_terminal(term, role):
    require(term.direction == DIRECTIONS[role] and term.signal == 'SIGNAL'
            and term.status in ('PLACED', 'FIRM', 'LOCKED', 'COVER'),
            f'physical endpoint direction, type or placement mismatch: {term.key}')
    require(not term.aliases, f'fixture BTerm alias on source-owned ITerm net: {term.key}')
    actual = (term.name, term.pin, term.direction)
    require(actual in term.members, f'ITerm absent from physical net incidence: {term.key}')
    drivers = [m for m in term.members if m[2] in ('OUTPUT', 'INOUT')]
    require(drivers == ([actual] if role == 'driver' else []),
            f'unexpected physical drivers on native leg: {term.key}')


def prepare_members(catalog, users, cuts):
    _, _, members, unresolved = expand(users, catalog)
    require(members and not unresolved, 'missing or unexpanded source demand')
    require(len({m['id'] for m in members}) == len(members), 'duplicate logical member')
    require(set(cuts) == {m['id'] for m in members}, 'explicit source-owned cut coverage differs')
    selections = {}
    for m in members:
        cut = cuts[m['id']]
        require(cut['driver'] == m['driver'] and sorted(cut['sinks']) == m['sinks'],
                f'catalog differs from explicit source cut: {m["id"]}')
        for key, role in [(m['driver'],'driver'), *((x,'sink') for x in m['sinks'])]:
            require(key not in selections, f'ITerm claimed by multiple cuts: {key}')
            selections[key] = role
    return members, selections


def layout(path, top_name):
    import pya
    result = pya.Layout()
    result.read(str(path))
    top = result.cell(top_name)
    require(top is not None and top in list(result.top_cells()), f'raw GDS top identity absent: {top_name}')
    return result, top


def raw_box(rect, units, dbu):
    import pya
    exact = [v/(units*dbu) for v in rect]
    require(all(abs(v-round(v)) < 1e-7 for v in exact), 'native rectangle not on exact GDS grid')
    return pya.Box(*(round(v) for v in exact))


def full_mask(stream, cell, layer, boxes, units, recursive, label):
    import pya
    index = stream.find_layer(*layer)
    require(index is not None, f'raw GDS layer absent: {label}')
    for rect in boxes:
        box = raw_box(rect, units, stream.dbu)
        if recursive:
            region = pya.Region(cell.begin_shapes_rec_overlapping(index, box))
        else:
            region = pya.Region()
            for shape in cell.shapes(index).each_overlapping(box):
                if shape.is_box():
                    region.insert(shape.box)
                elif shape.is_polygon():
                    region.insert(shape.polygon)
                elif shape.is_path():
                    region.insert(shape.path.polygon())
        require((pya.Region(box) - region.merged()).is_empty(), f'claimed access lacks full raw GDS copper: {label} {rect}')


def leaf_access(term, windows, proof, parent, top, layer, units, openroad, exporter, geometry):
    """Verify an independent leaf BTerm to its exact placed parent ITerm."""
    import pya
    require(term.master_type == 'BLOCK' and term.orient == 'R0',
            f'unsupported direct hard leaf access transform: {term.key}')
    require(all((M10,'iterm-pin',tuple(w)) in term.shapes for w in windows),
            f'M10 boxes are not exact hard leaf ITerm shapes: {term.key}')
    leaf_odb, leaf_gds = (bound_file(proof[k]) for k in ('odb', 'gds'))
    extracted = bound_file(proof['spef'])
    leaf, master = layout(leaf_gds, term.master)
    require(leaf.dbu == parent.dbu, 'parent and independent hard leaf raw grids differ')
    local = [(a - term.x, b - term.y, c - term.x, d - term.y) for a, b, c, d in windows]
    full_mask(leaf, master, layer, local, units, True, term.key)
    staged = parent.cell(term.master)
    require(staged is not None, 'placed parent hard leaf master GDS absent')
    origin = raw_box((term.x,term.y,term.x+1,term.y+1),units,parent.dbu)
    require(any(parent.cell(i.cell_index).name==term.master and not i.cplx_trans.is_mirror()
                and i.cplx_trans.angle==0 and i.cplx_trans.mag==1
                and (i.cplx_trans.disp.x,i.cplx_trans.disp.y)==(origin.left,origin.bottom)
                for i in top.each_inst()), 'raw GDS hard leaf placement does not match ODB')
    # The independent master may have a separately receipted fixture access
    # overlay away from this pin. The selected window has exact raw equality.
    full_mask(parent, staged, layer, local, units, True, term.key)
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        evidence = export_odb(leaf_odb, [(term.name, term.pin)], root, openroad, exporter, geometry,
                              leaf_bterm=True)
        exported = [line.split('\t') for line in evidence.read_text(encoding='utf-8').splitlines()]
    rows = [r for r in exported if r[0] == 'LEAF_BTERM']
    require(rows and all(r[1]==term.pin and r[2]==term.direction and r[3]==M10 for r in rows),
            f'independent ODB leaf BTerm identity mismatch: {term.key}')
    observed = {tuple(int(x) for x in r[4:]) for r in rows}
    require(set(local) <= observed, f'independent ODB leaf access rectangle differs: {term.key}')
    members = {(r[1], r[2]) for r in exported if r[0] == 'LEAF_MEMBER' and r[3] == term.direction}
    reached = leaf_resistor_path(extracted, term.pin, term.direction, members)
    require(reached, f'independent leaf SPEF BTerm has no resistance path: {term.key}')
    return {'leaf_view_sha256': {key: proof[key]['sha256'] for key in ('odb', 'gds', 'spef')},
            'local_m10_boxes_dbu': local,
            'extracted_leaf_iterms': [list(item) for item in sorted(reached)]}


def leaf_resistor_path(path, pin, direction, members):
    """Check a finite resistor path between exact leaf BTerm and a real ITerm."""
    graph = defaultdict(set)
    internal = {}
    active = False
    found = False
    in_res = False
    names = {}
    delimiter = ':'
    with path.open(encoding='utf-8') as source:
        for line in source:
            fields = line.split()
            if not fields:
                continue
            if fields[0] == '*DELIMITER':
                delimiter = fields[1]
            elif not active and len(fields) == 2 and fields[0][1:].isdigit() and fields[0][0] == '*':
                names[fields[0]] = fields[1]
            elif fields[0] == '*D_NET':
                graph.clear()
                internal.clear()
                active = True
                found = in_res = False
            elif active and fields[0] == '*P' and names.get(fields[1], fields[1]) == pin and fields[2] == direction[0]:
                found = True
                port_node = fields[1]
            elif active and fields[0] == '*I' and fields[2] == direction[0]:
                instance, term = fields[1].rsplit(delimiter, maxsplit=1)
                member = (names.get(instance, instance), term)
                if member in members:
                    internal[fields[1]] = member
            elif active and fields[0] == '*RES':
                in_res = True
            elif active and fields[0]=='*END':
                if found:
                    reached = {port_node}
                    pending = [port_node]
                    while pending:
                        for node in graph[pending.pop()]-reached:
                            reached.add(node)
                            pending.append(node)
                    return {internal[node] for node in reached & internal.keys()}
                active = in_res = False
            elif active and found and in_res and len(fields)==4:
                _, a, b, value = fields
                resistance = float(value)
                if 0 <= resistance < float('inf'):
                    graph[a].add(b)
                    graph[b].add(a)
    return set()


def export_odb(odb, items, output, openroad, exporter, geometry, leaf_bterm=False):
    select = output/'selected-iterms.tsv'
    select.write_text(''.join(f'{inst}\t{pin}\n' for inst,pin in items),encoding='utf-8')
    evidence = output/'exact-odb-iterms.tsv'
    env = {**os.environ, 'ITERM_ODB':str(odb), 'ITERM_GEOMETRY':str(geometry),
           'ITERM_LIST':str(select), 'ITERM_DEF_READBACK':str(output/'readback.def'),
           'ITERM_NETLIST_READBACK':str(output/'readback.v'),
           'ITERM_LEAF_BTERM':'1' if leaf_bterm else '0'}
    with evidence.open('w',encoding='utf-8') as stdout:
        result = subprocess.run([openroad,'-no_init','-exit',str(exporter)],env=env,stdout=stdout,
                                stderr=subprocess.STDOUT,check=False)
    require(result.returncode==0, f'OpenDB terminal export failed: {evidence}')
    return evidence


def view_receipts(config):
    require(set(config['views']) == set(VIEWS), 'missing or extra native source views')
    return {name:{'path':str(bound_file(config['views'][name])),
                  'sha256':config['views'][name]['sha256']} for name in VIEWS}


def build(config, config_hash, catalog, users, output, openroad, exporter, geometry):
    require(config.get('schema')==SCHEMA, 'unsupported true ITerm source contract')
    views = view_receipts(config)
    members, roles = prepare_members(catalog, users, config['cuts'])
    access = config['access']
    require(set(access)==set(roles), 'explicit source-owned access coverage differs')
    selectors = []
    for key, record in access.items():
        instance, pin = record['instance'], record['pin']
        require(all(isinstance(field, str) and field and not any(c in field for c in '\t\r\n')
                    for field in (instance, pin)) and key == f'{instance}/{pin}', f'expected exact ITerm key: {key}')
        selectors.append((instance, pin))
    evidence = export_odb(Path(views['odb']['path']),selectors,output,openroad,exporter,geometry)
    block, terms = parse_export(evidence)
    name, units, *bounds = block
    require(set(terms)==set(roles), 'OpenDB export endpoint coverage differs')
    for key, role in roles.items():
        require_terminal(terms[key], role)
        require(terms[key].net == access[key]['native_net'], f'ODB native owner differs: {key}')
    for member in members:
        owner_nets = [terms[key].net for key in [member['driver'], *member['sinks']]]
        require(owner_nets[0] not in owner_nets[1:],
                'declared open cut is already joined in the source ODB')
        require(len(owner_nets) == len(set(owner_nets)), 'multiple landings claimed for one native sink leg')
    require(file_hash(output/'readback.def')==views['def']['sha256'], 'ODB and declared DEF readback differ')
    require(file_hash(output/'readback.v')==views['netlist']['sha256'], 'ODB and declared netlist readback differ')
    raw, top = layout(Path(views['gds']['path']),name)
    layer_map = config['native_gds_layers']
    require(M10 in layer_map and all(LAYER.fullmatch(name) and isinstance(pair, list) and len(pair) == 2
                                     and all(type(n) is int and 0 <= n <= 65535 for n in pair)
                                     for name, pair in layer_map.items())
            and len({tuple(pair) for pair in layer_map.values()}) == len(layer_map), 'invalid raw GDS layer map')
    patches = net_patches(output/'readback.def',{t.net for t in terms.values()})
    endpoints = {}
    for key, role in roles.items():
        source, term = access[key], terms[key]
        windows = source['m10_boxes_dbu']
        require(windows and all(isinstance(r,list) and len(r)==4 and all(type(x) is int for x in r)
                                and contains(bounds,r) for r in windows), f'invalid exact access boxes: {key}')
        kind = source['kind']
        if kind=='parent_routed_iterm':
            full_mask(raw, top, layer_map[M10], windows, units, False, key)
            copper = connected_native_access(term,patches[term.net])
            by_layer = defaultdict(set)
            for layer, _, rectangle in copper:
                by_layer[layer].add(rectangle)
            require(all(covered(window, by_layer[M10]) for window in windows),
                    f'M10 access outside native component: {term.key}')
            for layer, boxes in sorted(by_layer.items()):
                require(layer in layer_map, f'no raw GDS mapping for connected native layer: {layer}')
                # The stream can instantiate a via cell instead of flattening
                # its enclosures and cut into the parent cell.
                full_mask(raw, top, layer_map[layer], sorted(boxes), units, True, f'{key} {layer}')
            physical = {'raw_connected_rectangles_by_layer': {layer: len(boxes) for layer, boxes in by_layer.items()}}
        elif kind=='independent_hard_leaf':
            physical = leaf_access(term, windows, source['independent_leaf'], raw, top, layer_map[M10],
                                   units, openroad, exporter, geometry)
        else:
            raise ValueError(f'unsupported ITerm access proof: {kind}')
        endpoints[key] = {'odb_term':key,'native_net':term.net,'role':role,'source_master':term.master,
                          'source_member_iterms':[list(member) for member in sorted(term.members)],
                          'source_access_kind':kind,'source_access_evidence':physical,
                          'm10_shapes':[{'layer':'M10','object':f'ITERM/{key}/M10/{i}',
                                                                  'rect_dbu':r} for i,r in enumerate(windows)]}
    for key, ep in endpoints.items():
        for other, dst in endpoints.items():
            if other <= key or ep['native_net']==dst['native_net']:
                continue
            require(not any(intersects(a['rect_dbu'], b['rect_dbu']) for a in ep['m10_shapes'] for b in dst['m10_shapes']),
                    'native M10 landing touches a foreign endpoint')
    provenance = {'scope':'native_true_iterm_open_cut','source_config_sha256':config_hash,
                  'source_native_odb_sha256':views['odb']['sha256'],'actual_odb_endpoint_export_sha256':file_hash(evidence),
                  'actual_odb_def_readback_sha256':views['def']['sha256'],
                  'actual_odb_netlist_readback_sha256':views['netlist']['sha256'],
                  'odb_geometry_exporter_sha256':file_hash(geometry)}
    if 'related_constructive_proof' in config:
        proof = config['related_constructive_proof']
        bound_file(proof)
        provenance['related_constructive_proof_sha256'] = proof['sha256']
    base = {'schema_version':VERSION,'state':'candidate','base_id':f'native-iterm:{name}:{views["odb"]["sha256"][:16]}',
            'dbu_per_micron':units,'bounds_dbu':bounds,'views':views,'endpoints':endpoints,
            'fixed_native_nets':{},'native_inventory':provenance}
    request = elaborate(users,catalog,base,provenance)
    require(request['status'] == 'endpoint_binding_complete', 'true ITerm cut does not bind completely')
    return base,request


def main():
    source = Path(os.environ['ITERM_SOURCE_CONFIG']).resolve()
    source_hash = os.environ['ITERM_SOURCE_SHA256']
    require(file_hash(source)==source_hash,'true ITerm source config fingerprint differs')
    config = read_json(source)
    catalog, users = (read_json(bound_file(config[k])) for k in ('catalog','users'))
    rules = read_json(bound_file(config['rules'])) if 'rules' in config else None
    if rules:
        from backend import gds_layer_map
        require(gds_layer_map(rules['technology'])['M10'] == config['native_gds_layers'][M10],
                'router and native GDS M10 layer mappings differ')
    output = Path(os.environ['ITERM_OUTPUT']).resolve()
    output.mkdir(parents=True,exist_ok=False)
    base, request = build(config,source_hash,catalog,users,output,os.environ['ITERM_OPENROAD'],
                          Path(__file__).resolve().with_name('export_true_iterms.tcl'),
                          Path(os.environ['ITERM_GEOMETRY']).resolve())
    payloads = {'base':base,'requirements':request}
    if rules:
        spec = bind_request(request,base,rules['technology'],rules.get('obstacles',[]))
        validate(spec)
        payloads['router-input'] = spec
    for name, value in payloads.items():
        (output/f'{name}.json').write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
