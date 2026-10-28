"""Repair the 26 proven full-C fixed-PG contacts; never replace the old C.

Move only the proven offending points within their local two-dimensional
patches. Original layer, shape, bus association, and 13184-net cohort stay
fixed. Screening is against original real metal/OBS, not a DRC qualification.
"""
from pathlib import Path
import argparse, hashlib, json, shutil
import numpy as np
import pandas as pd
import expand_candidates as expand


def prepare(root, out):
    root, out = Path(root), Path(out)
    assert not out.exists(), 'Refuse existing input directory'
    evidence = root / 'fixed_pg_rejections/llaccel_aux_full_C/proof.json'
    proof = json.loads(evidence.read_text(encoding='utf-8'))
    assert proof['all_actual_moved_pins_match_complete_original_C']
    assert proof['actual_PG_before_and_after_move_byte_identical']
    bad = sorted({q['pin'] for q in proof['contacts']})
    assert len(bad) == 26 and len(proof['contacts']) == 44
    raw = root / 'llaccel_aux_pin_coordinates.csv'
    d = pd.read_csv(raw, low_memory=False)
    a = d[d.plan == 'A'].set_index('pin')
    c = d[d.plan == 'C'].set_index('pin').copy()
    assert len(a) == len(c) == 13507 and len(c[c.moved]) == 13184
    cohort = sorted(c[c.moved].index)
    groups = pd.read_csv(root / 'llaccel_aux_groups.csv')
    groups = groups[groups.plan == 'C'].set_index('pin')
    assert groups.index.is_unique and set(bad) <= set(groups.index)
    pieces = []
    for chunk in pd.read_csv(root / 'physical/llaccel_aux/shapes.tsv.gz', sep='\t', chunksize=250000):
        pieces.append(chunk[chunk.layer.isin(['metal5', 'metal6'])])
    obs = pd.read_csv(root / 'physical/llaccel_aux/obstructions.tsv.gz', sep='\t')
    pieces.append(obs[obs.layer.isin(['metal5', 'metal6'])][['layer', 'x0', 'y0', 'x1', 'y1', 'net_id', 'kind']])
    index = expand.legacy.ShapeIndex(pd.concat(pieces, ignore_index=True))
    del pieces
    meta = json.loads((root / 'llaccel_aux.meta.json').read_text())
    dims = np.array(meta['die_dbu'], float) / 2000
    macros = np.array([r['bbox_dbu'] for r in meta['macros']], float).reshape(-1, 4) / 2000
    offsets = sorted((abs(i) + abs(j), i, j) for i in range(-16, 17) for j in range(-16, 17) if i or j)
    repairs = []
    c['incremental_revision'] = 'C_llsys_pg_r03'
    c['revision_reason'] = 'Original C retained; no changes'
    for key in ['toM6_existing_shape_risk', 'toM8_existing_shape_risk', 'toM10_existing_shape_risk']:
        c[key] = c[key].astype(object)
    for pin in bad:
        r = c.loc[pin]
        original = np.array([r.x_um, r.y_um], float)
        hx, hy = (r.x1_um - r.x0_um) / 2, (r.y1_um - r.y0_um) / 2
        others = c[(c.index != pin) & (c.layer == r.layer)][['x_um', 'y_um']].to_numpy(float)
        chosen = None
        for _, i, j in offsets:
            x, y = np.round((original + np.array([i, j]) * .56) / .005) * .005
            box = np.array([x-hx, y-hy, x+hx, y+hy])
            if box[0] < dims[0]+22 or box[1] < dims[1]+22 or box[2] > dims[2]-22 or box[3] > dims[3]-22:
                continue
            if len(macros) and np.any((box[0]-.56 < macros[:, 2]) & (box[2]+.56 > macros[:, 0]) & (box[1]-.56 < macros[:, 3]) & (box[3]+.56 > macros[:, 1])):
                continue
            if np.any((abs(others[:, 0]-x) < .56) & (abs(others[:, 1]-y) < .56)):
                continue
            if index.hits(r.layer, x, y, hx, hy, .14, int(r.net_id)):
                continue
            chosen = (x, y)
            break
        assert chosen is not None, (pin, 'No safe local candidate; never silently return to edge')
        x, y = chosen
        c.loc[pin, ['x_um', 'y_um', 'x0_um', 'y0_um', 'x1_um', 'y1_um']] = [x, y, x-hx, y-hy, x+hx, y+hy]
        c.loc[pin, ['pin_layer_overlap', 'pin_layer_basic_spacing_risk', 'macro_bbox_overlap']] = False
        c.loc[pin, 'revision_reason'] = 'Repair actual immutable PG contact in same local C patch; all original M5/M6 metal and available OBS screened; route/vias pending'
        for key in ['toM6_existing_shape_risk', 'toM8_existing_shape_risk', 'toM10_existing_shape_risk']:
            c.loc[pin, key] = 'UNKNOWN_FOR_INCREMENTAL_XY'
        repairs.append({'pin': pin, 'group': groups.loc[pin, 'group'], 'group_semantics': groups.loc[pin, 'semantic'],
                        'layer': r.layer, 'old_C_xy_um': original.tolist(), 'proposed_xy_um': [float(x), float(y)],
                        'rectangle_half_size_um': [float(hx), float(hy)], 'basic_spacing_screen_um': .14})
    for name, column in [('anchors', 'nearest_traced_endpoint_L1_um'), ('endpoints', 'nearest_direct_endpoint_L1_um')]:
        pp = pd.read_csv(root / 'physical/llaccel_aux' / (name+'.tsv.gz'), sep='\t')
        pp.pin = pp.pin.map(expand.legacy.norm)
        for pin in bad:
            pts = pp[pp.pin == pin][['x', 'y']].to_numpy(float)/2000
            c.loc[pin, column] = float(abs(pts-c.loc[pin, ['x_um', 'y_um']].to_numpy(float)).sum(axis=1).min()) if len(pts) else np.nan
    c['moved'] = (abs(c.x_um-a.x_um) > 1e-6) | (abs(c.y_um-a.y_um) > 1e-6)
    assert int(c.moved.sum()) == 13184
    assert len(set(map(tuple, c[['layer', 'x_um', 'y_um']].to_numpy()))) == 13507
    for key in ['layer', 'direction', 'use', 'net', 'net_id']:
        assert c[key].equals(a[key])
    assert np.allclose(c.x1_um-c.x0_um, a.x1_um-a.x0_um)
    assert np.allclose(c.y1_um-c.y0_um, a.y1_um-a.y0_um)
    out.mkdir(parents=True)
    c.reset_index().to_csv(out/'llaccel_aux_C_pg_r03_all_pins.csv', index=False, float_format='%.6f')
    selected = c.loc[cohort]
    selected.reset_index().to_csv(out/'llaccel_aux-C.csv', index=False, float_format='%.6f')
    with (out/'llaccel_aux-C.tcl').open('w', encoding='utf-8', newline='\n') as f:
        for pin, r in selected.iterrows():
            f.write('lappend relocations {'+f'{{{pin}}} {r.layer} {r.x_um:.6f} {r.y_um:.6f} {r.x1_um-r.x0_um:.6f} {r.y1_um-r.y0_um:.6f}'+'}\n')
    shutil.copy2(root/'coverage_gate.json', out/'coverage_gate.json')
    receipt = {'scope': 'PROPOSED_INCREMENTAL_LOCAL_PG_REPAIR; physical routing/DRC/via/RC/STA unverified',
               'all_signal_pins': 13507, 'selected_original_C_cohort': 13184, 'proposed_moved_count': 13184,
               'changed_vs_original_C': 26, 'repairs': repairs, 'original_C_sha256': hashlib.sha256(raw.read_bytes()).hexdigest(),
               'actual_fixed_PG_proof_sha256': hashlib.sha256(evidence.read_bytes()).hexdigest(),
               'preserved': 'All other C XY; all original layers/rectangles/net/direction/constants/bundles/cell/PDN/resources/allowed layers',
               'unverified': 'New access/vias/route/full DRC/GDS/parent/RC/STA; other original C signal occupancy risks need rerouting'}
    (out/'revision.json').write_text(json.dumps(receipt, indent=2)+'\n')
    (out/'selection.json').write_text(json.dumps({'llaccel_aux': {'pins': cohort, **receipt}}, indent=2)+'\n')
    (out/'input_hashes.json').write_text(json.dumps({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}, indent=2)+'\n')
    print('LLSYS_PG_REPAIR_PROPOSED', len(c), 'signals;', len(repairs), 'local repairs;', int(c.moved.sum()), 'still internal')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    prepare(args.root, args.out)
