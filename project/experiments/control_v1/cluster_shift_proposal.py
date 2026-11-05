"""Verify candidate placement translations before actual pin reconstruction.

This changes placement only. It grants no routing, electrical or timing result.
"""
import copy
import hashlib
import json
import math
from pathlib import Path


def apply(path, base_path, manifest_path, graph_path, base, manifest, graph):
    def sha(p):
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()

    proposal = json.loads(Path(path).read_text())
    assert set(proposal) == {'schema', 'candidate_only', 'whole_system_qualified',
                             'base_sha256', 'manifest_sha256', 'graph_sha256', 'shifts_um'}
    assert proposal['schema'] in ('control162-rigid-cluster-shifts/1',
                                  'control162-r-boundary-link-shifts/1')
    link_only = proposal['schema'] == 'control162-r-boundary-link-shifts/1'
    assert proposal['candidate_only'] is True and proposal['whole_system_qualified'] is False
    bindings = {str(p): sha(p) for p in (path, base_path, manifest_path, graph_path, Path(__file__))}
    for key, p in [('base_sha256', base_path), ('manifest_sha256', manifest_path), ('graph_sha256', graph_path)]:
        assert proposal[key] == bindings[str(p)], ('Proposal input binding', key)
    assert base['graph_sha256'] == proposal['graph_sha256']
    assert len(graph['instances']) == 345 and 'macro_r' in graph['instances']
    assert set(base['placements_um']) == set(base['orientations']) == set(graph['instances'])
    assert all(v == 0 for v in base['orientations'].values())
    links = graph['boundary_links']['links']
    assert len(links) == 316 and len({v['instance'] for v in links}) == 316
    parent = {n: n for n in graph['instances']}
    for row in links:
        assert graph['instances'][row['instance']] == 'control_link8'
        parent[row['instance']] = row['source_instance']
    clusters = set(parent.values())
    assert len(clusters) == 29
    shifts = proposal['shifts_um']
    if link_only:
        r_links = {row['instance'] for row in links if row['source_instance'] == 'macro_r'}
        assert 1 <= len(shifts) <= len(r_links) and set(shifts) <= r_links
    else:
        assert set(shifts) == clusters
    for name, delta in shifts.items():
        assert isinstance(delta, list) and len(delta) == 2
        assert all(type(v) in (int, float) and math.isfinite(v) and abs(v) <= (192 if link_only else 512)
                   and abs(v/4-round(v/4)) < 1e-9 for v in delta), name
    def shift(name):
        return shifts.get(name, (0, 0)) if link_only else shifts[parent[name]]

    changed = copy.deepcopy(base)
    for name, xy in base['placements_um'].items():
        changed['placements_um'][name] = [xy[i]+shift(name)[i] for i in range(2)]
        x, y = changed['placements_um'][name]
        w, h = manifest['leaves'][graph['instances'][name]]['die_um']
        assert x >= 128 and y >= 128 and x+w+128 <= base['width_um'] and y+h+128 <= base['height_um'], name
    # Independently reject overlap of the actual345 native rectangles.
    for i, name in enumerate(sorted(graph['instances'])):
        x, y = changed['placements_um'][name]
        w, h = manifest['leaves'][graph['instances'][name]]['die_um']
        for other in sorted(graph['instances'])[:i]:
            xx, yy = changed['placements_um'][other]
            ww, hh = manifest['leaves'][graph['instances'][other]]['die_um']
            assert x+w <= xx or xx+ww <= x or y+h <= yy or yy+hh <= y, (name, other)
    assert set(base['terminals']) == {'net_'+str(bit) for bit in graph['connections']}
    for bit, connection in graph['connections'].items():
        name = 'net_'+str(bit)
        ends = [connection['driver'], *connection['sinks']]
        assert len(ends) == len(base['terminals'][name])
        expected = []
        for end, xy in zip(ends, base['terminals'][name]):
            delta = [0, 0] if end['instance'] == 'TOP' else shift(end['instance'])
            expected.append([int(xy[i]+delta[i]/4) for i in range(2)])
        changed['terminals'][name] = expected
    all_points = [tuple(p) for points in changed['terminals'].values() for p in points]
    assert len(all_points) == len(set(all_points)), 'Translated terminal overlap'
    assert changed['external_grid_pins'] == base['external_grid_pins']
    proof = dict(candidate_only=True, whole_system_qualified=False, clusters=29, instances=345,
                 die_unchanged=True, orientations_unchanged=True, all_native_masks_unchanged=True,
                 relative_member_offsets_unchanged=not link_only, actual_pin_reconstruction_pending=True,
                 scope='Input proposal verified only. Caller must reconstruct every actual native signal/PG pin and compare before original cap diagnostic. Full native/geometry/PG/three-RC300MHz gates remain mandatory.')
    if link_only:
        proof.update(moved_r_boundary_links=sorted(n for n, delta in shifts.items() if any(delta)),
                     macro_r_position_unchanged=True)
    return changed, proof, bindings
