"""Assembly controls on sealed field data; native import is tested separately."""
import copy
import json
from pathlib import Path
import sys
from joint_rc import assemble,emit_spef
from joint_rc_native import fixture_edges


def parse_caps(text):
    caps={};ground={};section=None
    for line in text.splitlines():
        if line in ('*CAP','*RES','*CONN','*END'):section=line;continue
        if line.startswith('*D_NET'):section=None;continue
        if section!='*CAP':continue
        fields=line.split();assert len(fields)in (3,4)
        value=float(fields[-1]);assert value>0
        if len(fields)==3:
            assert fields[1]not in ground;ground[fields[1]]=value
        else:caps.setdefault(tuple(sorted(fields[1:3])),[]).append(value)
    assert all(len(values)==2 and values[0]==values[1]for values in caps.values())
    return ground,{pair:values[0]for pair,values in caps.items()}


def main(path):
    index=json.loads(Path(path).read_text(encoding='utf-8'))
    group=index['tasks']['capture-geometry-group']['artifacts']['capture-geometry-group.json']['content']
    assert group['passed'] is True;results={}
    for child in group['children']:
        data=child['capture-field-fv.json']['content'];assert data['passed'] is True
        nodes=data['nodes'];rows={net:series[-1]for net,series in data['field_rows'].items()}
        edges=fixture_edges(data['fixture'],nodes);model=assemble(nodes,edges,rows)
        text,instances,native=emit_spef(model);ground,caps=parse_caps(text)
        assert len(ground)==len(instances)==len(native)==sum(map(len,nodes.values()))
        assert len(caps)==len(nodes['target'])*len(nodes['near'])
        wrong,_,_=emit_spef(model,'rewired-coupling');_,rewired=parse_caps(wrong)
        assert set(caps)==set(rewired)and any(abs(v-rewired[k])>1e-5 for k,v in caps.items())
        degree=lambda values,node:sum(v for pair,v in values.items()if node in pair)
        assert all(abs(degree(caps,n)-degree(rewired,n))<1e-12 for pair in caps for n in pair)
        bad=[]
        for kind in ['missing-node','wrong-label','missing-capture','negative-resistance','disconnected','positive-coupling','nonfinite']:
            n,e,r=copy.deepcopy(nodes),copy.deepcopy(edges),copy.deepcopy(rows)
            if kind=='missing-node':n['target'].pop()
            elif kind=='wrong-label':r['target']['nodes'][0]='wrong'
            elif kind=='missing-capture':r['target']['captures']=[c for c in r['target']['captures']if c['net']!='near']
            elif kind=='negative-resistance':e['target'][0]['ohm']=-1
            elif kind=='disconnected':e['target'].pop()
            elif kind=='positive-coupling':next(c for c in r['target']['captures']if c['net']=='near')['partial'][0]=1
            else:r['target']['entries'][0]['partial'][0]=float('nan')
            try:assemble(n,e,r)
            except (AssertionError,KeyError):bad.append(kind)
            else:raise AssertionError('Accepted '+kind)
        results[data['fixture']]=dict(ground_nodes=len(ground),node_pair_couplings=len(caps),resistors=len(model['resistors']),
            actual_measured_source=True,symmetric_spef_entries=True,rewire_preserves_every_node_coupling_marginal=True,rejected=bad)
    print(json.dumps(dict(passed=True,scope='Pure assembly/serialization controls using run100 actual field outputs, not native importer or complete extraction qualification',fixtures=results),indent=2))


if __name__=='__main__':main(sys.argv[1])
