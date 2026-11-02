"""Metadata-only negative controls on an actual complete supply graph."""
import argparse,copy,hashlib,json
from pathlib import Path
from system_pg_audit import supply_graph


def main():
    p=argparse.ArgumentParser();p.add_argument('--graph',type=Path,required=True);a=p.parse_args()
    graph=json.loads(a.graph.read_text());supply_graph(graph)
    cases=[]
    for name in ('missing_sink','duplicate_sink','swapped_supply','wrong_direction','wrong_external_driver'):
        broken=copy.deepcopy(graph);c=broken['connections']['PG_VDD']
        if name=='missing_sink':c['sinks'].pop()
        elif name=='duplicate_sink':c['sinks'][-1]=copy.deepcopy(c['sinks'][0])
        elif name=='swapped_supply':c['sinks'][0]['pin']='VSS'
        elif name=='wrong_direction':c['sinks'][0]['direction']='output'
        else:c['driver']['pin']='clk'
        try:supply_graph(broken)
        except AssertionError:cases.append(name)
        else:raise AssertionError('Corrupt supply accepted: '+name)
    print(json.dumps(dict(passed=True,graph=str(a.graph),graph_sha256=hashlib.sha256(a.graph.read_bytes()).hexdigest(),
        actual_instances=len(graph['instances']),rejected_cases=cases,
        scope='Metadata-only actual graph and negative corruption checks. No native/upper PG qualification.')))


if __name__=='__main__':main()
