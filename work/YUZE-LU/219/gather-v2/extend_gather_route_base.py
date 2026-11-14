"""Import routed DMA endpoints without declaring the Gather provider reachable."""
import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path

from route_contract import read_base, require, validate_base


def routed_views(detail):
    views = {}
    for row in (detail/'results.sha256').read_text().splitlines():
        expected, name = row.split('  ', 1)
        path = Path(name)
        require(path.resolve().parent == detail.resolve(), 'foreign routed artifact')
        checksum = sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(4*1024*1024), b''):
                checksum.update(block)
        require(checksum.hexdigest() == expected, 'routed artifact changed')
        views[path.name] = {'path': str(path), 'sha256': expected}
    require(views.keys() == {'routes.tsv', 'dma-detail.odb', 'drc.rpt'}, 'incomplete route receipt')
    require((detail/'drc.rpt').stat().st_size == 0, 'DMA detail route has violations')
    return views


def extend(base, detail, members):
    views = routed_views(detail)
    existing = {name for name, pin in base['endpoints'].items() if pin['assembly'] == 'dma'}
    dx, dy = next(entry['translation_dbu'] for entry in base['assemblies'] if entry['id'] == 'dma')
    seen = set()
    for row in csv.DictReader((detail/'routes.tsv').read_text().splitlines(), delimiter='\t'):
        name = 'dma/' + row['pin']
        require(name not in seen and (name in existing or name in members), 'unexpected DMA port')
        seen.add(name)
        require(row['connected_route_object'] == '1', 'DMA endpoint has no lower wire')
        role = {'INPUT': 'sink', 'OUTPUT': 'driver'}[row['role']]
        rect = [int(row[key])+offset for key, offset in
                zip(('x0', 'y0', 'x1', 'y1'), (dx, dy, dx, dy))]
        endpoint = {
            'assembly': 'dma', 'odb_term': name, 'role': role, 'native_net': 'dma/' + row['net'],
            'm10_shapes': [{'layer': 'M10', 'object': name + '/M10/0', 'rect_dbu': rect}],
        }
        if name in existing:
            require(base['endpoints'][name] == endpoint, 'existing selected endpoint moved')
        else:
            require(members[name] == row['role'], 'client pin direction differs from audit')
            base['endpoints'][name] = endpoint
    require(seen == existing | members.keys(), 'incomplete DMA endpoint coverage')
    base['views'].update({'DMA.odb': views['dma-detail.odb'],
                          'DMA.endpoint_plan': views['routes.tsv'],
                          'DMA.lower_route_access': views['routes.tsv'],
                          'DMA.lower_route_drc': views['drc.rpt']})
    base['base_id'] += '-client3'
    base['provenance']['dma_lower_route_scope'] = (
        'Standalone DMA, existing M10 endpoint geometry plus client 3, no paired Gather provider')
    base['provenance']['dma_lower_route_source'] = str(detail/'results.sha256')
    validate_base(base)
    return base


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('base', 'detail', 'pins', 'out'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    base = read_base(args.base)
    members = {'dma/' + row['logical_pin']: row['direction'] for row in
               csv.DictReader(args.pins.read_text().splitlines(), delimiter='\t')}
    require(len(members) == 684, 'unexpected client pin inventory')
    result = extend(base, args.detail, members)
    require(len(result['endpoints']) == len(read_base(args.base)['endpoints']) + len(members),
            'client expansion did not add exactly its own terminals')
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'additional_dma_endpoints': len(members), 'dma_client': 3,
                      'base_catalogue_sha256': sha256(args.out.read_bytes()).hexdigest(),
                      'native_gather_service_routes_added': 0}, sort_keys=True))


if __name__ == '__main__':
    main()
