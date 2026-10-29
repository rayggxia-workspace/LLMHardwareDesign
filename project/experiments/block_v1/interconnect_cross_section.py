"""Independent2-D electrostatic sanity check of the declared coarse wire model.

Cell-centered finite volume, homogeneous dielectric, aligned rectangular metal.
This is an infinite-length ideal cross section, not a calibrated3-D stack or
an upper bound on all actual layouts. Conductors are fixed Dirichlet surfaces;
dielectric center-to-metal-face distance is half a cell, not a full cell.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time


def solve(h, half_width, height, neighbors=False, plate=False, boundary_weight=2.):
    import numpy as np
    from scipy.sparse import coo_matrix
    from scipy.sparse.linalg import spsolve
    nx, ny = round(2 * half_width / h), round(height / h)
    assert abs(nx * h - 2 * half_width) < 1e-9 and abs(ny * h - height) < 1e-9
    x = -half_width + (np.arange(nx) + .5) * h
    y = (np.arange(ny) + .5) * h
    xx, yy = np.meshgrid(x, y)
    fixed = np.zeros((ny, nx), bool)
    values = np.zeros((ny, nx))
    driven = np.zeros((ny, nx), bool)
    if not plate:
        driven = (abs(xx) < 1.) & (yy > .8) & (yy < 2.8)
        fixed |= driven
        values[driven] = 1.
        if neighbors:
            fixed |= ((abs(xx - 4) < 1.) | (abs(xx + 4) < 1.)) & (yy > .8) & (yy < 2.8)
    free = ~fixed
    ids = np.full((ny, nx), -1, dtype=np.int64)
    ids[free] = np.arange(int(free.sum()))
    count = int(free.sum())
    diagonal = np.zeros(count)
    rhs = np.zeros(count)
    rows, cols, data = [], [], []
    for dy, dx in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
        a = (slice(max(0, -dy), min(ny, ny-dy)), slice(max(0, -dx), min(nx, nx-dx)))
        b = (slice(max(0, dy), min(ny, ny+dy)), slice(max(0, dx), min(nx, nx+dx)))
        ai, bi = ids[a], ids[b]
        mask = ai >= 0
        both = mask & (bi >= 0)
        to_fixed = mask & (bi < 0)
        np.add.at(diagonal, ai[both], 1.)
        rows.append(ai[both]); cols.append(bi[both]); data.append(-np.ones(int(both.sum())))
        np.add.at(diagonal, ai[to_fixed], boundary_weight)
        np.add.at(rhs, ai[to_fixed], boundary_weight * values[b][to_fixed])
    edges = [(ids[0, :], 0.), (ids[-1, :], 1. if plate else 0.)]
    if not plate:
        edges += [(ids[:, 0], 0.), (ids[:, -1], 0.)]
    for edge, voltage in edges:
        valid = edge >= 0
        np.add.at(diagonal, edge[valid], boundary_weight)
        np.add.at(rhs, edge[valid], boundary_weight * voltage)
    rows.append(np.arange(count)); cols.append(np.arange(count)); data.append(diagonal)
    matrix = coo_matrix((np.concatenate(data), (np.concatenate(rows), np.concatenate(cols))), shape=(count,count)).tocsr()
    answer = spsolve(matrix, rhs)
    residual = float(np.linalg.norm(matrix @ answer - rhs) / np.linalg.norm(rhs))
    assert residual < 1e-9
    values[free] = answer
    assert values.min() > -1e-10 and values.max() <= 1 + 1e-10
    charge = 0.
    ground_charge = 0.
    energy_twice = 0.
    for dy, dx in [(0, 1), (1, 0)]:
        a = (slice(0, ny-dy), slice(0, nx-dx))
        b = (slice(dy, ny), slice(dx, nx))
        af, bf = free[a], free[b]
        pair_free = af & bf
        boundary = af ^ bf
        delta = values[a] - values[b]
        energy_twice += float(np.square(delta[pair_free]).sum())
        energy_twice += float(boundary_weight * np.square(delta[boundary]).sum())
        for source, sink in [(a,b), (b,a)]:
            metal = fixed[source] & free[sink]
            at_drive = metal & driven[source]
            at_ground = metal & ~driven[source]
            charge += float(boundary_weight * (1 - values[sink][at_drive]).sum())
            ground_charge -= float(boundary_weight * values[sink][at_ground].sum())
    # External metal planes use the same independently evaluated face flux.
    for edge_values, voltage in [(values[0,:],0.), (values[-1,:],1. if plate else 0.)] + (
            [] if plate else [(values[:,0],0.),(values[:,-1],0.)]):
        energy_twice += float(boundary_weight * np.square(edge_values-voltage).sum())
        if voltage == 1.:
            charge += float(boundary_weight * (1-edge_values).sum())
        else:
            ground_charge -= float(boundary_weight * edge_values.sum())
    assert abs(energy_twice / charge - 1) < 1e-8
    assert abs((charge + ground_charge) / charge) < 1e-8
    # epsilon in F/m times1e9 converts to fF/um for unit-length capacitance.
    epsilon_ff_per_um = 8.8541878128e-12 * 3.9 * 1e9
    return dict(h_um=h, half_width_um=half_width, height_um=height,
                unknowns=count, residual_relative=residual,
                capacitance_ff_per_um=charge * epsilon_ff_per_um,
                energy_capacitance_ff_per_um=energy_twice * epsilon_ff_per_um,
                charge_balance_relative=abs((charge + ground_charge) / charge))


def experiment(destination):
    os.environ['OPENBLAS_NUM_THREADS'] = '1'
    os.environ['MKL_NUM_THREADS'] = '1'
    import numpy as np
    import scipy
    started=time.time()
    expected = 8.8541878128e-12 * 3.9 * 1e9 * 4 / 1
    plate = solve(.1, 2, 1, plate=True)
    assert abs(plate['capacitance_ff_per_um']/expected-1) < 1e-9
    wrong_distance = solve(.1, 2, 1, plate=True, boundary_weight=1.)
    assert abs(wrong_distance['capacitance_ff_per_um']/expected-1) > .01
    rows={}
    for name, neighbors, upper_plane in [('lower-plane',False,False),
                                        ('lower-plane-neighbors',True,False),
                                        ('both-planes-neighbors',True,True)]:
        measured=[]
        for h in (.2,.1,.05):
            measured.append(solve(h,20,3.6 if upper_plane else 16,neighbors))
        far=solve(.1,30,3.6 if upper_plane else 24,neighbors)
        mesh_change=abs(measured[-1]['capacitance_ff_per_um']/measured[-2]['capacitance_ff_per_um']-1)
        domain_change=abs(far['capacitance_ff_per_um']/measured[1]['capacitance_ff_per_um']-1)
        rows[name]=dict(grids=measured,far_boundary=far,
                        last_mesh_relative_change=mesh_change,far_boundary_relative_change=domain_change,
                        numerical_gate_passed=mesh_change<.03 and domain_change<.02)
    result=dict(schema='coarse-wire-cross-section-sanity/1',
                passed=all(r['numerical_gate_passed']for r in rows.values()),
                original_formula_ff_per_um=.15539099611464,
                original_high_ff_per_um=.23308649417196,
                width_um=2,thickness_um=2,gap_below_um=.8,neighbor_spacing_um=2,
                upper_plane_gap_um=.8,epsilon_r=3.9,
                parallel_plate_control=dict(exact_ff_per_um=expected,measured=plate,
                                             wrong_face_distance_rejected=wrong_distance),
                cases=rows,versions=dict(numpy=np.__version__,scipy=scipy.__version__),
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                wall_seconds=time.time()-started,calibrated_12layer_rc_qualified=False,
                scope='Ideal infinite2-D wire over continuous grounded M10 plane; optionally two grounded same-layer neighbors and a continuous upper plane. Actual M10/M12 patterning,3-D crossings, dielectric calibration, switching/crosstalk and manufacturing are not modeled. Mesh/domain/energy/charge controls establish numerical consistency only; values are neither a calibrated stack nor universal bounds.')
    destination.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:dict(cap_ff_per_um=v['grids'][-1]['capacitance_ff_per_um'],
                             mesh_change=v['last_mesh_relative_change'],domain_change=v['far_boundary_relative_change'])
                      for k,v in rows.items()},indent=2))
    assert result['passed'],'Cross-section mesh/domain gate failed; preserve results and refine before use'


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('destination',type=Path)
    experiment(p.parse_args().destination)
