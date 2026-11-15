"""Graph-edge recognition for native recipes before whole-graph scheduling.

No task name, layer count, archived stage order, schedule or machine page is an
input. Recognition preserves every external dependency of each fused region.
"""
from collections import defaultdict
from copy import deepcopy

from canonicalize import canonicalize
from bind_attention_graph import bind_attention
from bind_rope_graph import bind_rope

VIEWS={'Reshape','Transpose','Slice','Unsqueeze','Squeeze','Expand','Identity'}

def build(original):
    graph=canonicalize(original)
    tasks={task['id']:task for task in graph['tasks']}
    producer={value:task['id'] for task in tasks.values() for value in task['outputs']}
    users=defaultdict(set)
    for task in tasks.values():
        for value in task['inputs']:users[value].add(task['id'])
    outputs=set(graph['outputs'])
    groups=[]
    claimed=set()

    def add(kind, members, details=None):
        members=set(members)
        if not members or members- tasks.keys() or members & claimed:
            raise ValueError('ambiguous or overlapping semantic recipe')
        ordered=[t for t in graph['tasks'] if t['id'] in members]
        inputs=list(dict.fromkeys(v for t in ordered for v in t['inputs'] if producer.get(v) not in members))
        boundary=list(dict.fromkeys(v for t in ordered for v in t['outputs'] if v in outputs or users[v]-members))
        source=list(dict.fromkeys(n for t in ordered for n in t.get('canonical_sources',[t['id']])))
        groups.append({'id':ordered[-1]['id'],'kind':kind,'members':[t['id'] for t in ordered],
                       'source_operations':source,'inputs':inputs,'outputs':boundary,'details':details or {}})
        claimed.update(members)

    attention, attention_unmatched=bind_attention(graph)
    rope, rope_unmatched=bind_rope(graph)
    for kind,rows in [('Attention',attention),('RoPE',rope)]:
        for row in rows:add(kind,row['operations'],deepcopy(row))

    def node(value,op):
        row=tasks.get(producer.get(value))
        return row if row and row['op']==op and not row.get('domain') else None

    weight_values=set(graph.get('weights',()))
    for row in graph.get('offline_weight_recipes',[]):
        if all(v in weight_values for v in row['inputs']):
            weight_values.update(row['outputs'])

    # SwiGLU region is recognized by its live graph edges, not layer names.
    for down in graph['tasks']:
        if down['id'] in claimed or down['op']!='MatMul' or down['inputs'][1] not in weight_values:continue
        mul=node(down['inputs'][0],'Mul')
        if not mul or len(mul['inputs'])!=2:continue
        for left,right in (mul['inputs'],mul['inputs'][::-1]):
            activation=node(left,'SiLU')
            up=node(right,'MatMul')
            gate=node(activation['inputs'][0],'MatMul') if activation else None
            if not up or not gate:continue
            if gate['inputs'][0]!=up['inputs'][0] or any(t['inputs'][1] not in weight_values for t in (gate,up)):continue
            members={t['id'] for t in (gate,activation,up,mul,down)}
            if members & claimed:continue
            # Shared intermediates must remain available to their other consumers.
            if any(v in outputs or users[v]-members for t in (gate,activation,up,mul) for v in t['outputs']):continue
            add('SwiGLUFFN',members,{'activation':gate['inputs'][0],
                'weights':[gate['inputs'][1],up['inputs'][1],down['inputs'][1]],
                'output':down['outputs'][0]})
            break

    for task in graph['tasks']:
        if task['id'] not in claimed:add('View' if task['op'] in VIEWS else task['op'],[task['id']],{'operation':deepcopy(task)})
    by_member={member:g['id'] for g in groups for member in g['members']}
    by_id={g['id']:g for g in groups}
    for group in groups:
        group['after']=sorted({by_member[producer[v]] for v in group['inputs'] if v in producer} - {group['id']})
        group['input_shapes']={v:graph['values'][v]['shape'] for v in group['inputs']}
        group['output_shapes']={v:graph['values'][v]['shape'] for v in group['outputs']}
    if set(by_member)!=set(tasks):raise ValueError('incomplete graph recipe coverage')
    # Stable Kahn order is a serialization of the dependency DAG, not a new edge.
    indegree={g['id']:len(g['after']) for g in groups}
    next_nodes=defaultdict(list)
    for group in groups:
        for parent in group['after']:next_nodes[parent].append(group['id'])
    ready=sorted(n for n,d in indegree.items() if not d)
    ordered=[]
    while ready:
        name=ready.pop(0);ordered.append(by_id[name])
        for child in next_nodes[name]:
            indegree[child]-=1
            if indegree[child]==0:ready.append(child)
        ready.sort()
    if len(ordered)!=len(groups):raise ValueError('recipe fusion introduces a dependency cycle')
    return {'schema':'algo1-native-recipe-graph/1','source_model_sha256':original['sha256'],
            'tasks':ordered,'values':graph['values'],'inputs':graph['inputs'],'outputs':graph['outputs'],
            'weights':graph.get('weights',[]),'offline_weight_recipes':graph.get('offline_weight_recipes',[]),
            'recognition_notes':{'attention_unmatched':attention_unmatched,'rope_unmatched':rope_unmatched},
            'coverage':{'original_tasks':len(original['tasks']),'canonical_tasks':len(tasks),
                        'recipes':len(groups),'covered_canonical_tasks':len(by_member)}}
