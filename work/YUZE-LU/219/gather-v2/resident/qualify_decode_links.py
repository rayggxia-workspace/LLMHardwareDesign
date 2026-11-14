"""Bind feedback receive and DMA pin requirements without granting a token provider."""
import argparse
import csv
from hashlib import sha256
import json
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from resident_gather_contract import demand
from route_contract import VERSION, elaborate, expand, read_base, validate_base


def checksum(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for arg in ('base', 'stored_bundle', 'place', 'dma_ports', 'sidecars', 'output'):
        cli.add_argument(arg, type=Path)
    args = cli.parse_args()

    spec = spec_from_file_location('resident_handoff', Path(__file__).with_name('publish-resident-gather.py'))
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    base = read_base(args.base)
    module.stage_base(base, args.place, args.dma_ports)
    stored = read_base(args.stored_bundle/'base.json')
    catalog = json.loads((args.stored_bundle/'catalog.json').read_bytes())
    transport = catalog['demands']['stored:C0->U0']
    translation, = (row['translation_dbu'] for row in base['assemblies'] if row['id'] == 'U0')
    dx, dy = translation
    rows = {}
    with (args.place/'landings.tsv').open() as table:
        for name, x0, y0, x1, y1 in csv.reader(table,delimiter='\t'):
            rows[name] = [int(x0)+dx,int(y0)+dy,int(x1)+dx,int(y1)+dy]
    # Preserve the definition of the original stored terminals. Recheck the
    # destination coordinates against the staged instance actually in use.
    _, _, members, _ = expand({'stored:C0->U0': []}, catalog)
    endpoints = {name for item in members for name in [item['driver'], *item['sinks']]}
    for name in endpoints:
        pin = stored['endpoints'][name]
        if name.startswith('U0/'):
            if [shape['rect_dbu'] for shape in pin['m10_shapes']] != [rows[name.split('/',1)[1]]]:
                raise ValueError(f'stored landing changed in the Gather revision: {name}')
        elif base['views']['C.netlist'] != stored['views']['C.netlist']:
            raise ValueError('stored source view differs from the placed candidate')
        if name in base['endpoints'] and base['endpoints'][name] != pin:
            raise ValueError(f'conflicting endpoint identity: {name}')
        base['endpoints'][name] = pin
    validate_base(base)
    config = {'schema_version': VERSION, 'demands': {'decode.index.transport':transport,
                                                     'gather.U0.dma3':demand('U0',3)}}
    sides = json.loads(args.sidecars.read_bytes())
    decode = [row for row in sides if row['input_source']['kind']=='previous_retired_token']
    if not decode or any(row['input_source']['word']!=512 for row in decode):
        raise ValueError('expected product-specific stored-word staging')
    uses = [{'task_id':f'decode-index-{row["step"]}', 'binding_id':row['pm_sha256']}
            for row in decode]
    proof = elaborate({group:uses for group in config['demands']}, config, base,
                      {'sidecar_sha256':checksum(args.sidecars)})
    if proof['status'] != 'endpoint_binding_complete':
        raise ValueError(proof['diagnostics'])
    report = {'status':'candidate_geometry_only', 'decode_boundaries':len(decode),
              'stored_terminal_members': sum(s['width'] for s in transport['signals']),
              'dma_members':650,'source_group':'C0','destination_group':'U0',
              'retired_token_producer_bound':False,
              'prerequisite':'retired_token_sram_commit_ack',
              'plan_sidecar_sha256':checksum(args.sidecars)}
    args.output.mkdir()
    for name, data in (('base',base),('catalog',config),('geometry-requirements',proof),
                       ('summary',report)):
        (args.output/f'{name}.json').write_text(json.dumps(data,sort_keys=True,indent=2)+'\n')
    print(json.dumps(report,sort_keys=True))


if __name__ == '__main__':
    main()
