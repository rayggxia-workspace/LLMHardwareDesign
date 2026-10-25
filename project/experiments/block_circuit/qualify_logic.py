"""Independent mapped-instance/stat/source qualification; no producer imports."""
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path


def load(p):
    return json.loads(Path(p).read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def need(v, message):
    if not v:
        raise ValueError(message)


def qualify(root, mode, override=None):
    folder = root/f'logic-map-m{mode}02'
    m = load(folder/'manifest.json') if override is None else override
    need(m['status'] == 'PASS_LOGIC_ONLY_REFERENCE_LIBRARY_MAPPING' and m['mode'] == mode, 'actual mapped mode')
    for item in m['artifacts']:
        p = folder/item['path']
        need(p.stat().st_size == item['bytes'] and sha(p) == item['sha256'], 'actual mapped artifact')
    prov = load(root/'nangate45-reference/provenance.json')
    need(prov == m['library'], 'external library provenance')
    for item in prov['files']:
        p = root/'nangate45-reference'/Path(item['path']).name
        need(p.stat().st_size == item['bytes'] and sha(p) == item['sha256'], 'official library bytes')
    reference = load(root/f'final-receipt-rtl-m{mode}-s003.json')
    need(reference['status'] == 'PASS_RTL_NUMERIC_PROTOCOL', 'qualified functional run')
    for name, digest in reference['source']['sources'].items():
        if name.startswith('project/rtl/'):
            need(m['source']['sources'][name] == digest, 'mapped RTL identical to accepted functional RTL')
    top = load(folder/'mapped.json')['modules']['wide_block']
    counts = dict(Counter(c['type'] for c in top['cells'].values()))
    stat = load(folder/'stat.json')['design']
    need(counts == stat['num_cells_by_type'], 'actual instance histogram versus native tool stat')
    need(counts.pop('ram128') == counts.pop('lut32') == 1, 'one common memory wrapper each')
    annotation_count = counts.pop('$scopeinfo', 0)
    need(not any(x.startswith('$') for x in counts), 'all remaining logic technology mapped')
    # A separate line-oriented Liberty reader obtains unmodified cell areas.
    areas = {}; cell = None
    for line in (root/'nangate45-reference/NangateOpenCellLibrary_typical.lib').read_text().splitlines():
        line = line.strip()
        if line.startswith('cell ('):
            cell = line.split('(', 1)[1].split(')', 1)[0].strip(' "')
        elif line.startswith('area') and ':' in line and cell is not None:
            areas[cell] = Decimal(line.split(':', 1)[1].split(';', 1)[0].strip())
    need(all(t in areas for t in counts), 'every mapped type has official cell area')
    area = sum(areas[t]*n for t, n in counts.items())
    need(abs(area-Decimal(str(stat['area']))) < Decimal('0.00001'), 'native tool area agrees with independent library sum')
    need(abs(area-Decimal(str(m['logic_area_um2']))) < Decimal('0.00001'), 'producer area label agrees with actual mapping')
    need(m['mapped_cells'] == counts and m['logic_cells'] == sum(counts.values()), 'producer histogram agrees')
    return {'mode': mode, 'logic_cells': sum(counts.values()), 'logic_area_um2': float(area),
            'mapped_DFF_X1': counts['DFF_X1'], 'scope_annotations': annotation_count,
            'manifest_sha256': sha(folder/'manifest.json'), 'netlist_sha256': sha(folder/'mapped.json'),
            'native_stat_sha256': sha(folder/'stat.json'), 'source': m['source']}


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); a.out.mkdir(exist_ok=False)
    rows = [qualify(a.root, mode) for mode in (0, 1)]
    negatives = []
    for mode in (0, 1):
        m = load(a.root/f'logic-map-m{mode}02/manifest.json')
        m['logic_area_um2'] += 1
        path = a.out/f'area-negative-m{mode}.json'
        path.write_text(json.dumps(m, indent=2)+'\n')
        try:
            qualify(a.root, mode, load(path))
        except ValueError as e:
            negatives.append({'path': path.name, 'sha256': sha(path), 'status': 'REJECTED_AFTER_REHASH', 'reason': str(e)})
        else:
            raise ValueError('altered producer area was trusted')
    b, l = rows
    result = {'schema': 'block-logic-independent80-v1', 'status': 'PASS_LOGIC_INSTANCE_SOURCE_AREA_RECEPTION',
              'rows': rows, 'logic_area_delta_um2': l['logic_area_um2']-b['logic_area_um2'],
              'logic_area_delta_percent': 100*(l['logic_area_um2']-b['logic_area_um2'])/b['logic_area_um2'],
              'semantic_negatives': negatives, 'library_provenance_sha256': sha(a.root/'nangate45-reference/provenance.json'),
              'limits': ['Logic only; both entire common frame/ROM wrappers excluded.',
                         'Research non-manufacturable Nangate45 model; no SRAM/ROM macro area, postroute, STA, power or mapped-gate functional equivalence acceptance.']}
    (a.out/'report.json').write_text(json.dumps(result, indent=2)+'\n')
    print(result['status'], result['logic_area_delta_percent'])


if __name__ == '__main__':
    main()
