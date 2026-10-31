"""Exact integer rectangle containment; diagnostic only, never a DRC waiver."""
import hashlib
import json
from pathlib import Path


def clipped_union_area(rectangles, target):
    x0, y0, x1, y1 = target
    assert x0 < x1 and y0 < y1
    cuts = sorted({x0, x1} | {max(x0, min(x1, b[i])) for b in rectangles for i in (0, 2)})
    area = 0
    for left, right in zip(cuts, cuts[1:]):
        intervals = sorted((max(y0, b[1]), min(y1, b[3])) for b in rectangles
                           if b[0] < right and b[2] > left and b[1] < y1 and b[3] > y0)
        previous = y0; length = 0
        for low, high in intervals:
            length += max(0, high - max(previous, low))
            previous = max(previous, high)
        area += (right - left) * length
    return area


def analyze():
    # Independent tiny controls include clipping, overlap, an interior hole,
    # disjoint rectangles and edge-touch-only rectangles with zero area.
    assert clipped_union_area([[-2, -2, 12, 12]], [0, 0, 10, 10]) == 100
    assert clipped_union_area([[0, 0, 7, 10], [3, 0, 10, 10]], [0, 0, 10, 10]) == 100
    assert clipped_union_area([[0, 0, 4, 10], [6, 0, 10, 10]], [0, 0, 10, 10]) == 80
    assert clipped_union_area([[0, 0, 10, 4], [0, 6, 10, 10]], [0, 0, 10, 10]) == 80
    assert clipped_union_area([[10, 0, 20, 10]], [0, 0, 10, 10]) == 0
    folder = Path(__file__).resolve().parent
    source = folder / 'block-v1-20261030-557/tasks/revision300-v-spacing-localize/revision300-v-physical-localization.json'
    raw = source.read_bytes()
    report = json.loads(raw)
    assert report['passed'] and report['source_database_unchanged']
    assert len(report['markers']) == 445
    rows = []
    for index, record in enumerate(report['markers']):
        marker = record['marker']; box = marker['bbox_dbu']
        shapes = record['same_net_nearby_rectangles']
        assert all(s['net'].replace('\\', '') == marker['net'].replace('\\', '') and s['layer'] == marker['layer'] for s in shapes)
        single = any(s['shape'] == 'wire' and s['bbox_dbu'][0] <= box[0] and s['bbox_dbu'][1] <= box[1]
                     and s['bbox_dbu'][2] >= box[2] and s['bbox_dbu'][3] >= box[3] for s in shapes)
        rows.append(dict(index=index, layer=marker['layer'], marker_area_dbu2=(box[2]-box[0])*(box[3]-box[1]),
                         covered_by_wire_or_via_area_dbu2=clipped_union_area([s['bbox_dbu'] for s in shapes if s['shape'] in ('wire', 'wire-via')], box),
                         entire_marker_inside_single_same_net_wire=single))
    assert sum(row['entire_marker_inside_single_same_net_wire'] for row in rows) == 440
    assert all(row['marker_area_dbu2'] == row['covered_by_wire_or_via_area_dbu2'] for row in rows)
    result = dict(source_report_sha256=hashlib.sha256(raw).hexdigest(), implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  independent_area_controls=5, rows=rows,
                  scope='Exact containment classification only. No checker waiver, geometric repair or physical acceptance. Marker report and original source databases are retained.')
    (folder / 'marker-union-containment.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    result = dict(source_report_sha256=result['source_report_sha256'], implementation_sha256=result['implementation_sha256'],
                  rows=[{k: row[k] for k in ('index', 'layer', 'entire_marker_inside_single_same_net_wire')} for row in rows], scope=result['scope'])
    (folder / 'marker-wire-containment.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    print('440 single-wire and445 union coverage;5 independent area controls PASS. Diagnostic only.')


if __name__ == '__main__':
    analyze()
