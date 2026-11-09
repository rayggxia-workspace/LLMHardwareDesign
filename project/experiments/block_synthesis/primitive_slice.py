"""Source-closed diagnostic cuts, preserving literal component proofs.

Boundary activations are explicit external inputs with full-source identity.
This does not fabricate their numeric values or claim the cut ran end to end.
"""
from copy import deepcopy


def select(model,program,names,source_sha256):
    ids={n['id']:n for n in program['instructions']}
    wanted=set(names)
    if not wanted or not wanted<=ids.keys():raise ValueError('invalid primitive slice selection')
    if len(source_sha256)!=64 or any(c not in '0123456789abcdef' for c in source_sha256):
        raise ValueError('full source SHA-256 required')
    p=deepcopy(program);m=deepcopy(model);boundary={};constants=set()
    # Constants stay literal instructions, preserving the full compiler's
    # narrow_literal proof rather than changing every literal to S32 input.
    for name in wanted:
        for source in ids[name]['inputs']:
            if source in wanted or source in program.get('initial_formats',{}):continue
            if source not in ids:raise ValueError('full source itself has an undeclared operand')
            n=ids[source]
            if n['op']=='Constant':constants.add(source);continue
            meta={k:deepcopy(n[k]) for k in ('shape','bits','exponent')}
            meta['boundary_source']={'primitive':source,'operation':n['op'],'source_sha256':source_sha256,
                'scope':'provided by enclosing graph; numeric values not supplied by this cut'}
            boundary[source]=meta
    kernels={ids[n]['kernel'] for n in wanted}
    p['instructions']=[deepcopy(n) for n in program['instructions'] if n['id'] in wanted|constants]
    p['initial_formats']={**p.get('initial_formats',{}),**boundary}
    selected=[n['id'] for n in program['instructions'] if n['id'] in wanted]
    p['outputs']={'last':selected[-1]}
    m['tasks']=[t for t in m['tasks'] if t['id'] in kernels]
    for name,meta in boundary.items():
        if name in m['values']:raise ValueError('SSA boundary collides with semantic value')
        m['values'][name]=deepcopy(meta)
    scope={'kind':'source-closed-primitive-cut-v1','source_sha256':source_sha256,
        'selected_primitives':selected,'literal_dependencies':sorted(constants),'external_boundaries':boundary,
        'excluded':'numeric boundary data, system/RTL/physical qualification and predecessor execution'}
    p['diagnostic_cut']=deepcopy(scope)
    return m,p,scope
