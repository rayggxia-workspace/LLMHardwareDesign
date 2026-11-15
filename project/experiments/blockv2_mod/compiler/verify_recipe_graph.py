"""Independent source coverage and cross-region dependency checks."""
from collections import Counter

def verify(original, lowered):
    source={t['id']:t for t in original['tasks']}
    owners={}
    for region in lowered['tasks']:
        for operation in region['source_operations']:
            if operation not in source or operation in owners:
                raise ValueError('lost/duplicate source ownership: '+operation)
            owners[operation]=region['id']
    if set(source)!=set(owners):raise ValueError('original graph is not fully covered')
    producers={v:t['id'] for t in original['tasks'] for v in t['outputs']}
    expected={r['id']:set() for r in lowered['tasks']}
    for task in original['tasks']:
        owner=owners[task['id']]
        for value in task['inputs']:
            parent=producers.get(value)
            if parent is not None and owners[parent]!=owner:
                expected[owner].add(owners[parent])
    actual={r['id']:set(r['after']) for r in lowered['tasks']}
    if expected!=actual:
        changed=[k for k in expected if expected[k]!=actual[k]]
        raise ValueError('fusion changed graph dependencies: '+str(changed[:5]))
    boundary={v for r in lowered['tasks'] for v in r['outputs']}
    if not set(original['outputs'])<=boundary:
        raise ValueError('graph output disappeared')
    return {'passed':True,'covered_original_operations':len(owners),
            'regions':len(lowered['tasks']),
            'cross_region_dependency_edges':sum(map(len,expected.values())),
            'recipe_kinds':dict(Counter(r['kind'] for r in lowered['tasks'])),
            'scope':'exact source partition and cross-region edges; not machine-code or numeric execution'}
