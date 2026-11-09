"""Ready native DAG actions, independent of model names and search scores.

Canonical row order is explicit. ``all`` enumerates every compatible subset
in that order; ``windows`` is a bounded contiguous-window action family.
Neither permits fusion of arithmetic or execution before an SSA dependency.
"""
from itertools import combinations
import json


class ReadyGraph:
    def __init__(self,tile,max_rows):
        graph=tile['graph'];self.nodes={n['id']:n for n in graph['operations'] if 'reuse_of' not in n}
        self.order=tuple(self.nodes);self.max_rows=max_rows
        self.writers={n['output']:n['id'] for n in self.nodes.values()}
        self.dependencies={name:frozenset(self.writers[v] for v in n['inputs'] if v in self.writers)
                           for name,n in self.nodes.items()}
        self.signatures={}
        for name,n in self.nodes.items():
            if n['kind']=='M':
                self.signatures[name]=(n['k'],n['width'],n['shift'],json.dumps(graph['objects'][n['output']]['abi'],sort_keys=True),
                    tuple((t['b'],t['coefficient'],t['scale_shift']) for t in n['terms']))

    def actions(self,completed,*,allow_batch=True,policy='windows'):
        if policy not in ('windows','all'):raise ValueError('unknown ready grouping policy')
        if not completed<=self.nodes.keys():raise ValueError('unknown completed native operation')
        ready=[n for n in self.order if n not in completed and self.dependencies[n]<=completed]
        result=[(n,) for n in ready]
        if not allow_batch:return result
        buckets={}
        for n in ready:
            if n in self.signatures:buckets.setdefault(self.signatures[n],[]).append(n)
        for names in buckets.values():
            for size in range(2,min(len(names),self.max_rows)+1):
                if policy=='all':result.extend(combinations(names,size))
                else:result.extend(tuple(names[i:i+size]) for i in range(len(names)-size+1))
        return result

    def future(self,completed,live):
        return set(live)|{v for name,n in self.nodes.items() if name not in completed for v in n['inputs']}
