"""Pure native expression identities and optional recomputation frontiers.

The original operation order survives. A repeated expression may be reused
only if an actual SRAM copy or acknowledged external backing survives; it
may instead execute its original native commands again. No arithmetic is
performed by an alias, and every original live-out keeps its own commit.
"""
from bisect import bisect_left,bisect_right
from copy import deepcopy


KIND='native-pointwise-reuse-frontier-v1'


def _signature(n,aliases,objects):
    inputs=[aliases.get(x,x) for x in n['inputs']]
    abi=objects[n['output']]['abi']
    if n['kind']=='M':
        return ('M',abi,n['k'],n['width'],n['shift'],tuple(inputs),
                tuple((aliases.get(t['a'],t['a']),aliases.get(t['b'],t['b']),t['coefficient'],t['scale_shift']) for t in n['terms']))
    if n['kind']=='E':return ('E',abi,n['opcode'],n['shift'],tuple(inputs))
    raise ValueError('native reuse only supports registered pure M/E operators')


def rewrite(source):
    if source.get('kind')!='native-pointwise-ssa-v1':raise ValueError('original native SSA graph required')
    aliases={};seen={};ops=[]
    for n in source['operations']:
        sig=_signature(n,aliases,source['objects']);representative=seen.setdefault(sig,n['output'])
        aliases[n['output']]=representative
        updated={**deepcopy(n),'inputs':[aliases.get(x,x) for x in n['inputs']],'output':representative}
        if n['kind']=='M':updated['terms']=[{**t,'a':aliases.get(t['a'],t['a']),'b':aliases.get(t['b'],t['b'])} for t in n['terms']]
        if representative!=n['output']:updated['reuse_of']=representative
        ops.append(updated)
    result={**deepcopy(source),'kind':KIND,'operations':ops,
            'primitive_outputs':{n:aliases[x] for n,x in source['primitive_outputs'].items()},
            'live_out':{n:aliases[x] for n,x in source['live_out'].items()},
            'external_commits':[{'primitive':n,'original_record':x,'record':aliases[x],
                                 'external_address':source['objects'][x]['external_address']}
                                for n,x in source['live_out'].items()],
            'reuse_proof':{'kind':'ordered-native-expression-equivalence-v1','source_graph':deepcopy(source)}}
    verify(result,source);return result


def verify(graph,source=None):
    """Check each claimed identity against an earlier equal native definition.

Does not call the optimizer/signature builder. Source binding is exact when
the registrar supplies its independently reconstructed original graph. The
event interpreter additionally allows per-element address/index relocation;
equivalence is parametric in opaque input words, not their runtime addresses.
"""
    if graph.get('kind')!=KIND:raise ValueError('native reuse graph kind differs')
    proof=graph.get('reuse_proof',{})
    if proof.get('kind')!='ordered-native-expression-equivalence-v1':raise ValueError('native reuse proof required')
    original=proof['source_graph']
    if source is not None and original!=source:raise ValueError('native reuse source binding differs')
    if source is not None and (graph['objects']!=source['objects'] or graph['index']!=source['index']):
        raise ValueError('native reuse source address/index binding differs')
    if original.get('kind')!='native-pointwise-ssa-v1' or len(graph['operations'])!=len(original['operations']):
        raise ValueError('native reuse original order/extent differs')
    if (set(graph['objects'])!=set(original['objects']) or graph['shape']!=original['shape'] or
        graph['primitives']!=original['primitives']):raise ValueError('native reuse objects/shape/region differ')
    for name,o in original['objects'].items():
        # Element relocation changes addresses and opaque input indices only.
        actual=graph['objects'][name]
        if ({k:v for k,v in actual.items() if k not in ('index','external_address')}!=
            {k:v for k,v in o.items() if k not in ('index','external_address')}):
            raise ValueError('native reuse object contract differs')
    aliases={};definitions={};seen_outputs=set()
    for old,n in zip(original['operations'],graph['operations']):
        if old['output'] in seen_outputs:raise ValueError('native reuse original is not SSA')
        if any(x not in original['objects'] or original['objects'][x]['kind']=='produced' and x not in seen_outputs for x in old['inputs']):
            raise ValueError('native reuse original input precedes its definition')
        seen_outputs.add(old['output']);expected=deepcopy(old)
        expected['inputs']=[aliases.get(x,x) for x in old['inputs']]
        if old['kind']=='M':expected['terms']=[{**t,'a':aliases.get(t['a'],t['a']),'b':aliases.get(t['b'],t['b'])} for t in old['terms']]
        elif old['kind']!='E':raise ValueError('native reuse contains an unregistered operation')
        out=n['output'];expected['output']=out
        if out!=old['output']:
            if out not in definitions or n.get('reuse_of')!=out:raise ValueError('native reuse lacks a previous definition')
            previous=definitions[out]
            def semantic(op):return {k:v for k,v in op.items() if k not in ('id','output','primitive','reuse_of')}
            if (semantic(expected)!=semantic(previous) or
                graph['objects'][old['output']]['abi']!=graph['objects'][out]['abi']):
                raise ValueError('native reuse expression is not bit-identical')
            expected['reuse_of']=out
        elif 'reuse_of' in n:raise ValueError('first native definition cannot be reused')
        if n!=expected:raise ValueError('native reuse changed native fields/order')
        aliases[old['output']]=out;definitions.setdefault(out,n)
    if (graph['primitive_outputs']!={n:aliases[x] for n,x in original['primitive_outputs'].items()} or
        graph['live_out']!={n:aliases[x] for n,x in original['live_out'].items()}):
        raise ValueError('native reuse output identity differs')
    commits=[{'primitive':n,'original_record':x,'record':aliases[x],
              'external_address':graph['objects'][x]['external_address']} for n,x in original['live_out'].items()]
    if graph.get('external_commits')!=commits:raise ValueError('native reuse lost an original external output commit')
    return {'passed':True,'logical_operations':len(graph['operations']),
            'optional_reuse_points':sum('reuse_of' in n for n in graph['operations']),
            'external_commits':len(commits)}


class Liveness:
    def __init__(self,graph):
        self.ops=graph['operations'];self.reads={};self.writes={};self.live=set(graph['live_out'].values())
        for i,n in enumerate(self.ops):
            for x in set(n['inputs']):self.reads.setdefault(x,[]).append(i)
            if n.get('reuse_of'):self.writes.setdefault(n['output'],[]).append(i)

    def may_discard(self,index,value):
        # Conservatively protect every input of an open native command. No M
        # accumulator is spilled/re-entered to implement recomputation.
        if index>=len(self.ops) or value in self.ops[index]['inputs']:return False
        uses=self.reads.get(value,());at=bisect_right(uses,index)
        next_use=uses[at] if at<len(uses) else len(self.ops) if value in self.live else float('inf')
        writes=self.writes.get(value,());at=bisect_left(writes,index)
        return at<len(writes) and writes[at]<=next_use
