"""Check real extracted graphs; legacy order exact and R fully prioritized."""
import argparse,copy,json
from pathlib import Path
from system_upper import priority_outputs

def inspect(path,expected):
    graph=json.loads(path.read_text());found=priority_outputs(graph);assert len(found)==expected
    sources={'macro_1','macro_2','macro_3','macro_4','macro_s','macro_t'}
    if graph.get('S_internal_drive'):sources.remove('macro_s')
    old=['net_'+bit for bit,c in graph['connections'].items()if c['driver']['instance']in sources]
    if 'macro_r'in graph['instances']:
        actual=['net_'+bit for bit,c in graph['connections'].items()if c['driver']['instance']=='macro_r']
        assert len(actual)==646 and set(found)==set(old)|set(actual)
        negative=copy.deepcopy(graph);del negative['connections'][actual[0][4:]]
        try:priority_outputs(negative)
        except AssertionError:pass
        else:raise AssertionError('Missing real native R output accepted')
    else:assert found==old,'Legacy priority membership/order changed'
    assert all(len({e['instance']for e in graph['connections'][name[4:]]['sinks']})==1 for name in found)
    assert all(graph['instances'][e['instance']]=='control_link8'for name in found for e in graph['connections'][name[4:]]['sinks'])
    return dict(passed=True,graph=str(path),priority_output_count=len(found),R_output_count=len(found)-len(old),legacy_subsequence_exact=[n for n in found if n in set(old)]==old)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--graph',type=Path,required=True);p.add_argument('--expected',type=int,required=True);a=p.parse_args();print(json.dumps(inspect(a.graph,a.expected)))
