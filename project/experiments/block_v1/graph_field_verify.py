"""Independent FV conductor-face flux for 3D graph-node origin partitions.

The Laplace matrix, boundary potentials and solver remain upstream. Only actual
conductor-face charges are grouped by their face positions; adjacent free-cell
centers are insufficient at bends, vias and non-axis-aligned Voronoi boundaries.
"""


def fixture_nodes(geometry):
    if geometry == 'branch':
        nodes=[('left',[-2.4,0,13.89]),('junction',[0,0,13.89]),
               ('right',[2.4,0,13.89]),('upper',[0,2.4,13.89])]
        edges=[('left','junction'),('junction','right'),('junction','upper')]
    else:
        assert geometry == 'via'
        nodes=[('left',[-2.4,0,11.09]),('lower',[1.6,0,11.09]),
               ('right',[2.4,0,11.09]),('upper',[1.6,0,13.89]),('end',[1.6,2.4,13.89])]
        edges=[('left','lower'),('lower','right'),('lower','upper'),('upper','end')]
    return nodes,edges


def fv_source(text):
    replacements=[
        ('    wire_cell, wire_net, wire_g = [], [], []',
         '    wire_cell, wire_net, wire_g = [], [], []\n    wire_pos = []'),
        ('            wire_g.append(gm)',
         '''            wire_g.append(gm)
            indices = np.nonzero(m)
            # Both sides share axes[k][i+1], independent of which cell is free.
            face = np.column_stack([axes[j][1:-1][indices[j]] if j==k
                                    else centers[j][indices[j]] for j in range(3)])
            wire_pos.append(face)'''),
        ('    wire_g = np.concatenate(wire_g)',
         '    wire_g = np.concatenate(wire_g)\n    wire_pos = np.concatenate(wire_pos)'),
        ('    matrix = np.zeros((len(names), len(names) + 1))',
         '''    assert names[0] == 'target'
    nodes = np.array(GRAPH_NODES, dtype=float)
    assert nodes.ndim == 2 and nodes.shape[1] == 3 and len(nodes) >= 3
    target = wire_net == 0
    delta = wire_pos[target,None,:] - nodes[None,:,:]
    bins = np.argmin(np.sum(delta*delta,axis=2),axis=1)
    partial = np.zeros((len(names)+1,len(nodes)))
    matrix = np.zeros((len(names), len(names) + 1))'''),
        ('            matrix[master, net] = EPS0 * np.sum(wire_g[s] * (v - phi[wire_cell[s]]))',
         '''            charge = EPS0 * wire_g[s] * (v - phi[wire_cell[s]])
            matrix[master, net] = np.sum(charge)
            if net == 0:
                partial[master] = np.bincount(bins,weights=charge,minlength=len(nodes))'''),
        ('    return names, matrix, n',
         '''    partial[-1] = -partial[:-1].sum(axis=0)
    assert np.allclose(partial[:-1].sum(axis=1),matrix[:,0],rtol=1e-10,atol=1e-12)
    return names, matrix, n, partial''')]
    for before,after in replacements:
        assert text.count(before)==1,before
        text=text.replace(before,after)
    return text
