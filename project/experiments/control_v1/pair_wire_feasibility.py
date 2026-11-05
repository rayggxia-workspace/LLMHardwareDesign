"""Necessary wire-only constraints shared by a whole pair of rigid macros.

Each possible relative nonoverlap direction reduces to intersection of exact
one-dimensional intervals. Empty intersections reject a placement family;
nonempty intersections never establish routing or timing acceptance.
"""
import itertools,json,math
from pathlib import Path
from placement_orientation import transform


def family(size_a,size_b,links,ra,rb,direction,ff):
    axis=0 if direction in ['E','W']else 1;free=1-axis
    separation=size_a[axis]if direction in ['E','N']else-size_b[axis]
    lower=-math.inf;upper=math.inf;low_net=high_net=None;negative=[]
    for link in links:
        aa=transform(link['a'],size_a,ra);bb=transform(link['b'],size_b,rb)
        required=abs(separation+bb[axis]-aa[axis]);radius=link['max_capacitance_ff']/ff-required
        center=aa[free]-bb[free]
        if radius < -1e-7:negative.append(dict(net=link['net'],missing_wire_budget_um=-radius))
        lo,hi=center-radius,center+radius
        if lo>lower:lower=lo;low_net=link['net']
        if hi<upper:upper=hi;high_net=link['net']
    feasible=not negative and lower<=upper+1e-7
    return dict(rotation_a=ra,rotation_b=rb,direction=direction,
                wire_only_necessary_constraints_feasible=feasible,interval_um=[lower,upper],
                lower_bound_net=low_net,upper_bound_net=high_net,
                negative_radius_count=len(negative),first_negative=negative[:1])


def inspect(manifest,graph,pins,report,out,sha):
    receipt_path=report.parent/'receipt.json';receipt=json.loads(receipt_path.read_text())
    assert receipt['passed']and receipt['stage']=='wire-cap-lower-bound-only'
    assert receipt['outputs'][report.name]==sha(report)
    for row in manifest['leaves'].values():
        odb=row['final_files']['6_final.odb'];assert receipt['inputs'][odb['path']]==odb['sha256']==sha(odb['path'])
    diagnostic=json.loads(report.read_text());assert diagnostic['executed']and diagnostic['research_model']
    spec=Path(__file__).resolve().parents[1]/'block_v1/technology-2um-v1.json';technology=json.loads(spec.read_text())
    geo=technology['geometry_um'];e=technology['electrical']
    ff=.0088541878128*e['relative_permittivity']*(geo['width']/geo['dielectric_gap']+2*geo['thickness']/geo['spacing'])
    assert math.isclose(ff,diagnostic['ff_per_um_base'],rel_tol=1e-12)
    drivers={row['net']:row for row in diagnostic['rows']};pairs={}
    def point(endpoint):
        pin=pins[graph['instances'][endpoint['instance']]][endpoint['pin']]
        if 'xy_um'in pin:return pin['xy_um']
        b=pin['box_dbu'];return[(b[0]+b[2])/4000,(b[1]+b[3])/4000]
    for bit,c in graph['connections'].items():
        name='net_'+bit
        if name not in drivers:continue
        driver=c['driver'];assert driver==drivers[name]['driver']
        limit=drivers[name]['physical_driver']['max_capacitance_ff']
        for sink in c['sinks']:
            if sink['instance']in ['TOP',driver['instance']]:continue
            a,b=sorted([driver['instance'],sink['instance']]);ends={driver['instance']:driver,sink['instance']:sink}
            pairs.setdefault((a,b),[]).append(dict(net=name,driver_instance=driver['instance'],a=point(ends[a]),b=point(ends[b]),max_capacitance_ff=limit))
    results=[]
    for(a,b),links in sorted(pairs.items()):
        size_a=manifest['leaves'][graph['instances'][a]]['die_um'];size_b=manifest['leaves'][graph['instances'][b]]['die_um']
        assert size_a[0]==size_a[1]and size_b[0]==size_b[1]
        variants={}
        for variant,factor in e['estimate_variants'].items():
            cases=[]
            for ra,rb,direction in itertools.product(range(4),range(4),['E','W','N','S']):
                cases.append(family(size_a,size_b,links,ra,rb,direction,ff*factor))
            variants[variant]=dict(all_64_rigid_nonoverlap_families_infeasible=all(not c['wire_only_necessary_constraints_feasible']for c in cases),
                                   feasible_family_count=sum(c['wire_only_necessary_constraints_feasible']for c in cases),cases=cases)
        source_only={}
        for driver in [a,b]:
            subset=[link for link in links if link['driver_instance']==driver]
            if not subset:continue
            source_variants={}
            for variant,factor in e['estimate_variants'].items():
                cases=[family(size_a,size_b,subset,ra,rb,direction,ff*factor)
                       for ra,rb,direction in itertools.product(range(4),range(4),['E','W','N','S'])]
                source_variants[variant]=dict(all_64_rigid_nonoverlap_families_infeasible=all(not c['wire_only_necessary_constraints_feasible']for c in cases),
                    feasible_family_count=sum(c['wire_only_necessary_constraints_feasible']for c in cases),cases=cases)
            source_only[driver]=dict(constrained_links=len(subset),variants=source_variants)
        results.append(dict(instances=[a,b],constrained_links=len(links),variants=variants,each_driver_alone=source_only))
    result=dict(executed=True,passed=False,whole_system_qualified=False,
        inputs={str(report):sha(report),str(receipt_path):sha(receipt_path),str(spec):sha(spec),str(Path(__file__)):sha(Path(__file__))},
        impossible_pair_counts={v:sum(r['variants'][v]['all_64_rigid_nonoverlap_families_infeasible']for r in results)for v in e['estimate_variants']},pairs=results,
        scope='Failure-only joint necessary condition. All four rotations per square macro, all four nonoverlap directions, zero gap and unrestricted continuous transverse displacement. Original capacitance, via/load and route detours omitted. A feasible interval is not a feasible system or route.')
    (out/'pair-wire-feasibility.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
