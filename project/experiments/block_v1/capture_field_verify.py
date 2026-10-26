"""Independent Dirichlet boundary-patch FV reference for joint node charge.

Reuse the pinned Laplace matrix and uniform-net reference solves. Only the
right-hand side changes for auxiliary boundary basis functions: exciting one
surface patch is not a claim that the physical wire is several electrodes.
"""


def fv_source(text):
    from graph_field_verify import fv_source as origin_source
    text = origin_source(text)
    before = '    return names, matrix, n, partial'
    after = '''    # Actual conductor faces, with stable nearest-node tie breaking.
    face_bins = {}
    for net,name in enumerate(names):
        points = np.array(CAPTURE_REFERENCE_NODES[name],dtype=float)
        assert points.ndim == 2 and points.shape[1] == 3 and len(points) >= 2
        p = wire_pos[wire_net == net]
        delta = p[:,None,:] - points[None,:,:]
        face_bins[net] = np.argmin(np.sum(delta*delta,axis=2),axis=1)
    joint = {}
    for drive,name in enumerate(names):
        on_net = wire_net == drive
        on_indices = np.flatnonzero(on_net)
        count = len(CAPTURE_REFERENCE_NODES[name])
        for receiver in range(len(names)):
            if receiver != drive:
                joint[names[receiver]+'|'+name] = np.zeros((len(CAPTURE_REFERENCE_NODES[names[receiver]]),count))
        for j in range(count):
            on = on_indices[face_bins[drive] == j]
            assert len(on) > 0, 'FV capture patch has no exposed boundary faces'
            rhs = np.zeros(n)
            np.add.at(rhs,wire_cell[on],wire_g[on])
            phi = ml.solve(rhs,tol=1e-11,accel='cg',maxiter=500)
            for receiver in range(len(names)):
                if receiver == drive:
                    continue
                target_faces = wire_net == receiver
                charge = -EPS0 * wire_g[target_faces] * phi[wire_cell[target_faces]]
                key = names[receiver]+'|'+name
                joint[key][:,j] = np.bincount(face_bins[receiver],weights=charge,minlength=joint[key].shape[0])
    for receiver in range(len(names)):
        for drive in range(len(names)):
            if receiver == drive:
                continue
            key = names[receiver]+'|'+names[drive]
            assert np.isclose(joint[key].sum(),matrix[drive,receiver],rtol=1e-8,atol=1e-10)
            reverse = names[drive]+'|'+names[receiver]
            assert np.allclose(joint[key],joint[reverse].T,rtol=1e-8,atol=1e-10)
            if receiver == 0:
                assert np.allclose(joint[key].sum(axis=1),partial[drive],rtol=1e-8,atol=1e-10)
    return names, matrix, n, partial, joint'''
    assert text.count(before) == 1
    return text.replace(before, after)
