"""Bind the vocabulary consumer to actual P0 auxiliary SRAM terminals."""
import argparse
from collections import Counter
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path

from route_contract import digest, read_base


MEMBERS = (
    ('req_valid', 1, 'aux_valid', 'sink'),
    ('req_ready', 1, 'aux_ready', 'driver'),
    ('req_write', 1, 'aux_write', 'sink'),
    ('req_address', 10, 'aux_address', 'sink'),
    ('req_tag', 32, 'aux_tag', 'sink'),
    ('rsp_valid', 1, 'aux_rsp_valid', 'driver'),
    ('rsp_ready', 1, 'aux_rsp_ready', 'sink'),
    ('rsp_tag', 32, 'aux_rsp_tag', 'driver'),
    ('rsp_data', 128, 'aux_rsp_data', 'driver'),
)


def run(base_path, def_reader, vocabulary_link, output):
    spec = spec_from_file_location('stock_def_reader', def_reader)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    base = read_base(base_path)
    placed, = (row for row in base['assemblies'] if row['id'] == 'P0')
    view = base['views'][placed['views']['def']]
    path = base_path.parent/view['path']
    h = sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1<<20), b''):
            h.update(block)
    if h.hexdigest() != view['sha256']:
        raise ValueError('P0 DEF differs from base')
    members = [(role, net if width==1 else f'{net}[{bit}]', direction)
               for role,width,net,direction in MEMBERS for bit in range(width)]
    ports = module.def_ports(path, {pin for _,pin,_ in members})
    dx,dy = placed['translation_dbu']
    status, detail = Counter(), []
    for role,pin,direction in members:
        rec = ports.get(pin)
        if rec is None:
            status['missing_bterm'] += 1
            detail.append(dict(role=role,pin=pin,status='missing_bterm'))
            continue
        def_dir, def_net, shapes = rec
        expected = 'INPUT' if direction == 'sink' else 'OUTPUT'
        if expected != def_dir:
            raise ValueError(f'{pin} direction changed')
        code = 'm10_shape_present' if shapes else 'missing_m10_shape'
        status[code] += 1
        name = 'P0/'+pin
        shapes = [[x0+dx,y0+dy,x1+dx,y1+dy] for x0,y0,x1,y1 in shapes]
        detail.append(dict(role=role,pin=name,direction=direction,native_net='P0/'+def_net,
                           status=code,m10_shapes_dbu=shapes))
    receipt = json.loads(vocabulary_link.read_bytes())
    result = dict(schema='block-v2-vocabulary-aux-endpoints/1', stage='endpoint_inventory',
                  base_sha256=digest(base), vocabulary_link_sha256=sha256(vocabulary_link.read_bytes()).hexdigest(),
                  source_view_sha256=h.hexdigest(), tile_calls=receipt['volume']['calls'],
                  terminal_controller='unbound', p0_ports=len(members), counts=status,
                  endpoints=detail)
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(ports=len(members),counts=status),sort_keys=True))


if __name__ == '__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    for field in ('base_path','def_reader','vocabulary_link','output'):
        cli.add_argument(field,type=Path)
    run(**vars(cli.parse_args()))
