"""Selected Yosys port / literal ANSI header / Liberty / LEF interface join.

This is an interface consistency check, not an RTL equivalence proof.
JSON bit IDs are module-local; aliases/constants do not erase physical pins.
"""
from collections import defaultdict
import json
import math
from pathlib import Path
import re
import sys

from evidence import sha
from liberty_profile import parse_liberty
sys.path.append(str(Path(__file__).resolve().parent.parent / 'macro_endpoints'))
from lef_profile import parse_lef


def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError('Duplicate JSON key: ' + key)
        obj[key] = value
    return obj


def json_view(data):
    return json.loads(data, object_pairs_hook=unique_object)


def header_ports(data, macro):
    text = data.decode('utf-8')
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
    match = re.search(r'\bmodule\s+' + re.escape(macro) +
                      r'\s*(?:import\s+[A-Za-z_]\w*::\*;\s*)?\((.*?)\)\s*;', text, re.S)
    if not match:
        raise ValueError('Unsupported boundary header')
    ports, inherited = {}, None
    for item in match.group(1).split(','):
        item = item.strip()
        declaration = re.fullmatch(r'(input|output)\s+(logic|wire|cmd_t)\s*'
                                   r'((?:\[\s*\d+\s*:\s*\d+\s*\]\s*)*)([A-Za-z_]\w*)', item)
        if declaration:
            direction, kind, shape, name = declaration.groups()
            dims = [[int(a), int(b)] for a, b in re.findall(r'\[\s*(\d+)\s*:\s*(\d+)\s*\]', shape)]
            if kind == 'cmd_t' and dims:
                raise ValueError('Packed dimensions of unresolved named type are unsupported')
            inherited = {'direction': direction, 'type': kind, 'packed_dimensions': dims,
                         'declared_width': None if kind == 'cmd_t' else math.prod(abs(a-b)+1 for a,b in dims),
                         'width_source': 'Yosys elaboration; cmd_t definition not captured' if kind == 'cmd_t'
                         else 'literal ANSI packed dimensions'}
        elif inherited is not None and re.fullmatch(r'[A-Za-z_]\w*', item):
            name = item
        else:
            raise ValueError('Unsupported ANSI declaration: ' + item)
        if name in ports:
            raise ValueError('Duplicate boundary port: ' + name)
        ports[name] = dict(inherited)
    return ports


def logical_ports(data, boundary, macro):
    obj = json_view(data)
    module = obj['modules'][macro]
    declarations = header_ports(boundary, macro)
    if set(declarations) != set(module['ports']):
        raise ValueError('Boundary/Yosys port set mismatch')
    ports, bits, by_id, constants = {}, {}, defaultdict(list), []
    for name, port in module['ports'].items():
        decl = declarations[name]
        ids = port['bits']
        width, offset, upto = len(ids), port.get('offset', 0), port.get('upto', 0)
        direction = port['direction']
        if (not width or type(offset) is not int or type(upto) is not int or upto not in (0, 1)
                or direction not in ('input', 'output') or direction != decl['direction']
                or decl['declared_width'] not in (None, width)):
            raise ValueError('Invalid logical width/direction/index: ' + name)
        dims = decl['packed_dimensions']
        if len(dims) == 1:
            left, right = dims[0]
            if offset != min(left, right) or upto != int(left < right):
                raise ValueError('Boundary/Yosys index ordering mismatch: ' + name)
        elif len(dims) > 1:
            # Explicit selected profile: descending, zero-based packed arrays
            # are flattened by Yosys into the zero-based vector in these inputs.
            if offset or upto or any(right != 0 or left < right for left,right in dims):
                raise ValueError('Unsupported multidimensional flattening: ' + name)
        elif decl['type'] != 'cmd_t' and (offset or upto):
            raise ValueError('Scalar offset/upto is unsupported: ' + name)
        vector = bool(dims) or width > 1
        expanded = []
        for pos, bit_id in enumerate(ids):
            if not ((type(bit_id) is int and bit_id >= 0) or (type(bit_id) is str and bit_id in ('0','1','x','z'))):
                raise ValueError('Invalid Yosys connection bit')
            bit_index = offset + (width-1-pos if upto else pos) if vector else None
            bit_name = name + ('[' + str(bit_index) + ']' if vector else '')
            if bit_name in bits:
                raise ValueError('Duplicate expanded logical bit')
            row = {'bit_name': bit_name, 'port': name, 'position_lsb_first': pos, 'hdl_index': bit_index,
                   'direction': direction, 'yosys_bit': bit_id,
                   'yosys_pointer': '/modules/' + macro + '/ports/' + name + '/bits/' + str(pos)}
            bits[bit_name] = row
            expanded.append(bit_name)
            if isinstance(bit_id, str):
                constants.append({'bit_name': bit_name, 'value': bit_id})
            else:
                by_id[bit_id].append(bit_name)
        ports[name] = {'direction': direction, 'width': width, 'offset': offset, 'upto': upto,
                       'signed': port.get('signed', 0), 'bits': expanded, 'boundary': decl}
    return {'creator': obj['creator'], 'macro': macro, 'ports': ports, 'bits': bits,
            'aliases': [{'yosys_bit': i, 'bit_names': names} for i,names in sorted(by_id.items()) if len(names)>1],
            'constants': constants, 'source_sha256': sha(data), 'boundary_sha256': sha(boundary)}


def join_views(logical, lib, lef):
    if lib['cell']['raw_name'] != logical['macro'] or lef['macro']['name'] != logical['macro']:
        raise ValueError('Macro/cell name mismatch')
    lp = {p['name']: p for p in lef['macro']['pins']}
    lib_signal = [p for p in lib['cell']['bits'] if p.get('kind') != 'pg_pin']
    lib_pg = [p for p in lib['cell']['bits'] if p.get('kind') == 'pg_pin']
    lb = {p['bit_name']: p for p in lib_signal}
    if len(lp) != len(lef['macro']['pins']) or len(lb) != len(lib_signal):
        raise ValueError('Duplicate physical/library bit')
    # Dedicated Liberty pg_pin may be absent in generated Liberty: preserve
    # ordinary VDD/VSS pin direction and use LEF USE as the PG classifier.
    pg_lib = {p['bit_name']: p for p in lib_pg}
    if len(pg_lib) != len(lib_pg):
        raise ValueError('Duplicate PG Liberty pin')
    if set(pg_lib) & set(lb):
        raise ValueError('Ambiguous ordinary/PG Liberty pin')
    signal = {n:p for n,p in lp.items() if p['use'] in ('SIGNAL', 'CLOCK')}
    pg = {n:p for n,p in lp.items() if p['use'] in ('POWER', 'GROUND')}
    if set(signal) | set(pg) != set(lp):
        raise ValueError('Unclassified LEF pin USE')
    if set(signal) != set(logical['bits']) or (set(lb) | set(pg_lib)) != set(lp):
        raise ValueError('Logical/Liberty/LEF name-set mismatch')
    rows = {}
    for name, bit in logical['bits'].items():
        library, physical = lb[name], signal[name]
        if library['effective_direction'] != bit['direction'] or physical['direction'].lower() != bit['direction']:
            raise ValueError('Three-view direction mismatch: ' + name)
        rows[name] = {**bit, 'liberty': library, 'lef': physical,
                      'classification': 'shared_clock' if name == 'clk' else 'signal',
                      'legal_access_verified': False}
    power = []
    for name, physical in pg.items():
        library = lb.get(name, pg_lib.get(name))
        if name in pg_lib:
            pg_type = library['fields']['pg_type']['value']
            expected_use = 'POWER' if pg_type in ('primary_power','backup_power','internal_power') else (
                'GROUND' if pg_type in ('primary_ground','backup_ground','internal_ground') else None)
            if expected_use != physical['use']:
                raise ValueError('Unresolved or mismatched Liberty pg_type/LEF USE')
        if name in lb and library['effective_direction'] != physical['direction'].lower():
            raise ValueError('PG ordinary-pin direction mismatch')
        power.append({'bit_name': name, 'classification': physical['use'].lower(), 'liberty': library,
                      'lef': physical, 'supply_connectivity_verified': False})
    return {**logical, 'bits': rows, 'power': power,
            'liberty_metadata': {k:v for k,v in lib.items() if k not in ('cell','ast')},
            'liberty_cell': {k:v for k,v in lib['cell'].items() if k != 'bits'},
            'lef_metadata': {k:v for k,v in lef.items() if k != 'macro'},
            'source_hashes': {'elab.json': logical['source_sha256'], 'boundary.sv': logical['boundary_sha256'],
                              'liberty': lib['source_sha256'], 'lef': lef['source_sha256']}}


def load_view(folder, macro):
    folder = Path(folder)
    candidate, name = macro['id'], macro['macro']
    logical = logical_ports((folder/candidate/'elab.json').read_bytes(),
                            (folder/candidate/'boundary.sv').read_bytes(), name)
    lib = parse_liberty((folder/candidate/(name+'_typ.lib')).read_bytes(), candidate+'/'+name+'_typ.lib')
    lef = parse_lef((folder/(candidate+'.lef')).read_bytes(), candidate+'.lef')
    return join_views(logical, lib, lef)
