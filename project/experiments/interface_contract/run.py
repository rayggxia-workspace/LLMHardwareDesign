"""Build a deterministic boundary contract joined to three selected views."""
import argparse
import csv
import io
import json
from pathlib import Path
import shutil
from evidence import RUN_SOURCES, encoded, git, index, now, provenance, sha, validate_snapshot
from graph import build_graph
from views import load_view

LIMITS = {
    'rtl_equivalence_verified': False, 'timing_arc_coverage_verified': False,
    'legal_signal_access_verified': False, 'pg_connectivity_verified': False,
    'new_matched_macro_views_verified': False, 'physical_PPA_or_H2_verified': False,
}


def csv_bytes(rows, keys):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=keys, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def derive(folder):
    folder = Path(folder)
    cfg, captured, comparisons = validate_snapshot(folder)
    views = {m['id']: load_view(folder, m) for m in cfg['macros']}
    raw = json.loads((folder/'contract.json').read_bytes())
    validation = raw['tasks']['top-contract']['validation']
    if validation['passed'] is not True or validation['exact_bit_identity'] is not True:
        raise ValueError('Pinned upstream wiring evidence did not pass')
    graph = build_graph(validation['top_contract'], views)
    rows, macros = [], {}
    for candidate, view in views.items():
        macros[candidate] = {
            'macro': view['macro'], 'ports': len(view['ports']), 'signal_bits': len(view['bits']),
            'input_bits': sum(r['direction']=='input' for r in view['bits'].values()),
            'output_bits': sum(r['direction']=='output' for r in view['bits'].values()),
            'pg_pins': len(view['power']), 'aliases': view['aliases'], 'constants': view['constants'],
            'yosys_creator': view['creator'], 'source_hashes': view['source_hashes'],
            'three_view_names_widths_directions': 'PASS',
            'named_type_widths': {n:p['boundary']['width_source'] for n,p in view['ports'].items()
                                  if p['boundary']['declared_width'] is None},
        }
        for name, bit in view['bits'].items():
            rects = [r for port in bit['lef']['ports'] for r in port['rects']]
            rows.append({'candidate': candidate, 'bit_name': name, 'port': bit['port'],
                         'lsb_position': bit['position_lsb_first'], 'hdl_index': bit['hdl_index'],
                         'direction': bit['direction'], 'yosys_bit': bit['yosys_bit'],
                         'liberty_raw_name': bit['liberty']['raw_name'], 'liberty_line': bit['liberty']['line'],
                         'lef_line': bit['lef']['line'], 'lef_use': bit['lef']['use'],
                         'rect_count': len(rects), 'layers': '|'.join(sorted({r['layer'] for r in rects})),
                         'classification': bit['classification'], 'legal_access_verified': False})
    connection_rows = []
    for item in graph['connections']:
        connection_rows.append({'group': item['group'], 'offset': item['offset'],
                                'driver_candidate': item['driver']['candidate'], 'driver_bit': item['driver']['name'],
                                'sink_candidate': item['sink']['candidate'], 'sink_bit': item['sink']['name'],
                                'net': item['net']})
    summary = {'schema': 1, 'input_version': cfg['input_version'],
               'capture_sha256': sha((folder/'capture.json').read_bytes()),
               'producer_hash_comparisons': len(comparisons), 'macros': macros, 'graph': graph['summary'],
               'scope': 'Selected frozen wave2-06 boundary consistency; reuses existing Issue7 wiring evidence',
               'limitations': LIMITS}
    return {'views.json': encoded(views), 'graph.json': encoded(graph), 'summary.json': encoded(summary),
            'producer-comparisons.json': encoded(comparisons),
            'bits.csv': csv_bytes(rows, list(rows[0])),
            'connections.csv': csv_bytes(connection_rows, list(connection_rows[0]))}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit('Use a NEW output directory')
    prov, started = provenance(RUN_SOURCES), now()
    outputs = derive(a.inputs)
    a.out.mkdir(parents=True)
    shutil.copytree(a.inputs, a.out/'inputs')
    validate_snapshot(a.out/'inputs')
    if sha((a.out/'inputs/capture.json').read_bytes()) != json.loads(outputs['summary.json'])['capture_sha256']:
        raise AssertionError('Input snapshot changed during execution')
    if git('status','--porcelain') or git('rev-parse','HEAD') != prov['source_commit']:
        raise AssertionError('Source changed during execution')
    for name, data in outputs.items():
        (a.out/name).write_bytes(data)
    manifest = {'schema': 1, 'started_utc': started, 'finished_utc': now(), 'provenance': prov,
                'input_manifest_sha256': sha((a.inputs/'capture.json').read_bytes()), 'files': index(a.out)}
    (a.out/'manifest.json').write_bytes(encoded(manifest))
    print(json.dumps(json.loads(outputs['summary.json'])))


if __name__ == '__main__':
    main()
