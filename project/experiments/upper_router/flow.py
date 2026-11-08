"""General #220 plan -> resource assembly -> bit nets -> routed backend view.

Resource interface contracts are library inputs, never inferred from model names.
Tool-side elaboration/placement is not conditional on system RTL qualification.
"""
import argparse
import json
from pathlib import Path

from resource_base import assemble, instances_from_hardware, load_library, place
from route_contract import VERSION, from_plan, verify_requirements, selected_demands, digest, expand
from place_search import optimize as optimize_placement
from adapter import bind_request, failure_feedback
from backend import emit
from check import verify
from search import route


def library_catalog(instances, library):
    """Instantiate resource-local signal templates, preserving {bit} expansion."""
    demands = {}
    def instantiate(value):
        if isinstance(value,str):return value.replace('{group}',instance)
        if isinstance(value,list):return [instantiate(v) for v in value]
        if isinstance(value,dict):return {instantiate(k):instantiate(v) for k,v in value.items()}
        return value
    for instance, template in sorted(instances.items()):
        for name, definition in library[template].get('capabilities', {}).get('interfaces', {}).items():
            name = name.replace('{group}', instance)
            if name in demands:
                raise ValueError('duplicate instantiated resource interface: '+name)
            demands[name] = instantiate(definition)
    return {'schema_version':VERSION, 'demands':demands}


def run(ir, plan, library, rules, output, *, catalog=None, gap_dbu=0,
        alignment_dbu=1, rounds=8, max_expansions=100000, via_resistance_ohm):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    def write(name,value):
        (output/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    instances=instances_from_hardware(ir['hardware'],library)
    catalog=library_catalog(instances,library) if catalog is None else catalog
    positions,bounds=place(instances,library,gap_dbu=gap_dbu,alignment_dbu=alignment_dbu)
    base=assemble(instances,library,positions,bounds)
    _,_,members,_=expand(selected_demands(ir,plan),catalog)
    physical=[m for m in members if all(p in base['endpoints'] for p in [m['driver']]+m['sinks'])]
    positions,bounds,placement=optimize_placement(instances,library,physical,
        gap_dbu=gap_dbu,alignment_dbu=alignment_dbu)
    base=assemble(instances,library,positions,bounds)
    write('placement-search.json',placement)
    request=from_plan(ir,plan,catalog,base)
    verify_requirements(request,selected_demands(ir,plan),catalog,base,request['source'])
    write('base.json',base);write('catalog.json',catalog);write('requirements.json',request)
    common={'source':request['source'],'base_sha256':digest(base),'request_sha256':request['sha256'],
            'physical_qualified':False,'resource_instances':sorted(instances),
            'native_or_external_realizations':len(request.get('realizations',[]))}
    if request['unresolved']:
        result={**common,'status':'resource_binding_incomplete','diagnostics':request['unresolved'],
                'scope':'Missing physical resource interface descriptions; no new RTL prerequisite inferred'}
        write('flow-result.json',result)
        return result
    technology=dict(rules['technology'],bounds=bounds)
    spec=bind_request(request,base,technology,rules.get('obstacles',[]))
    write('spec.json',spec)
    routes=route(spec,rounds=rounds,max_expansions=max_expansions)
    verify(spec,routes);write('routes.json',routes)
    write('routing-feedback.json',failure_feedback(request,routes,str(output/'routes.json')))
    if routes['failed']:
        result={**common,'status':'route_search_incomplete','failed':routes['failed'],
                'scope':'Candidate search failure; not a proof of physical infeasibility'}
    else:
        emit(spec,routes,output/'backend',base['dbu_per_micron'],via_resistance_ohm=via_resistance_ohm)
        result={**common,'status':'backend_geometry_exported','routed_nets':len(routes['routes']),
                'scope':'DEF and via LEF exported; actual ODB/GDS/RC/timing validation remains a separate gate'}
    write('flow-result.json',result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('ir','plan','library','rules','output'):p.add_argument(name,type=Path)
    p.add_argument('--catalog',type=Path)
    p.add_argument('--gap-dbu',type=int,required=True)
    p.add_argument('--alignment-dbu',type=int,default=1)
    p.add_argument('--via-resistance-ohm',type=float,required=True)
    p.add_argument('--rounds',type=int,default=8)
    p.add_argument('--max-expansions',type=int,default=100000)
    a=p.parse_args();read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    result=run(read(a.ir),read(a.plan),load_library(a.library),read(a.rules),a.output,
               catalog=read(a.catalog) if a.catalog else None,gap_dbu=a.gap_dbu,
               alignment_dbu=a.alignment_dbu,rounds=a.rounds,max_expansions=a.max_expansions,
               via_resistance_ohm=a.via_resistance_ohm)
    print(json.dumps(result))
    if result['status']!='backend_geometry_exported':raise SystemExit(2)
