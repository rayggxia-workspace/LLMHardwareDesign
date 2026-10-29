"""Finite geometry-based, coupon-informed RC/STA; explicit research assumptions."""
import json
from pathlib import Path
import re
from decimal import Decimal
from interconnect_spef import sha

ROUTE_RUN='block-v1-20261029-921'


def bound(folder,name):
    receipt=json.loads((folder/'receipt.json').read_text());assert receipt['passed']
    p=folder/name;assert sha(p)==receipt['outputs'][name]
    return json.loads(p.read_text()),receipt


def paths(text):
    """Parse actual two-pin DEF centerlines, including layer changes and vias."""
    section=re.search(r'(?ms)^NETS \d+ ;\n(.*?)^END NETS',text).group(1)
    result={}
    for entry in re.split(r'(?m)^\s*- ',section)[1:]:
        name=entry.split()[0];edges=[];nodes=set()
        for route in re.split(r'\+ ROUTED |\bNEW ',entry)[1:]:
            layer=re.match(r'(metal\d+)\b',route).group(1);current=None
            for token in re.finditer(r'\(\s*([*\d-]+)\s+([*\d-]+)(?:\s+[-\d]+)?\s*\)|\b((?:BV1_)?via(?:10|11)[A-Za-z0-9_]*)\b',route):
                if token[3]:
                    assert current is not None
                    level=int(re.search(r'via(\d+)',token[3])[1])
                    a=('metal%d'%level,*current);b=('metal%d'%(level+1),*current)
                    nodes.update((a,b));edges.append(dict(a=a,b=b,length_um=0.,via=level))
                else:
                    point=tuple(current[i] if v=='*' else int(v) for i,v in enumerate((token[1],token[2])))
                    a=(layer,*point);nodes.add(a)
                    if current is not None and point!=current:
                        assert point[0]==current[0] or point[1]==current[1]
                        edges.append(dict(a=(layer,*current),b=a,length_um=sum(abs(point[i]-current[i])for i in (0,1))/2000,via=None))
                    current=point
        # Split centerline wires at every actual same-net junction.
        split=[]
        for e in edges:
            if e['via'] is not None:split.append(e);continue
            a,b=e['a'],e['b']
            middle=[p for p in nodes if p[0]==a[0] and min(a[1],b[1])<=p[1]<=max(a[1],b[1]) and min(a[2],b[2])<=p[2]<=max(a[2],b[2])]
            middle.sort()
            for x,y in zip(middle,middle[1:]):
                split.append(dict(a=x,b=y,length_um=(abs(x[1]-y[1])+abs(x[2]-y[2]))/2000,via=None))
        unique={tuple(sorted((tuple(e['a']),tuple(e['b'])))):e for e in split}
        adjacent={p:set()for p in nodes}
        for a,b in unique:adjacent[a].add(b);adjacent[b].add(a)
        seen=set();todo=[next(iter(nodes))]
        while todo:
            n=todo.pop()
            if n not in seen:seen.add(n);todo.extend(adjacent[n])
        assert seen==nodes,('Disconnected centerline graph',name,len(seen),len(nodes))
        result[name]=list(unique.values())
    return result


def prepare_pair(root,out,cpus,run,pair):
    from interconnect_spef import prepare
    from interconnect_experiment import restore_physical
    assert cpus==16
    routed=(out.parents[2]/ROUTE_RUN/'tasks' if pair in ('mt','ts') else out.parent)/('linkclose-route-'+pair)
    record,receipt=bound(routed,'linkclose-route.json')
    for name in ('route-inputs.json','geometry.tsv','routed.def','routed.odb'):
        assert sha(routed/name)==receipt['outputs'][name]
    inputs=json.loads((routed/'route-inputs.json').read_text());native=inputs['native']
    command=['klayout','-b','-r',root/'project/experiments/block_v1/linkclose_geometry.rb',
        '-rd','request='+str(routed/'route-inputs.json'),'-rd','geometry='+str(routed/'geometry.tsv'),
        '-rd','spec='+str(root/'project/experiments/block_v1/technology-2um-v1.json'),'-rd','report='+str(out/'geometry.json')]
    run(command,'geometry.log');assert json.loads((out/'geometry.json').read_text())['passed']
    graph=paths((routed/'routed.def').read_text());assert set(graph)=={l['id']for l in inputs['links']}
    for l in inputs['links']:
        edges=graph[l['id']];points={tuple(e[k])for e in edges for k in ('a','b')}
        for key in ('source_xy_um','sink_xy_um'):
            endpoint=('metal10',*[round(x*2000)for x in l[key]])
            assert endpoint in points,('Native centerline endpoint shifted',l['id'],key,endpoint)
        for xy in l.get('extra_sink_xy_um',[]):
            assert ('metal10',*[round(x*2000)for x in xy])in points
        l['edges']=edges;l['routed_length_um']=sum(e['length_um']for e in edges)
        assert l['routed_length_um']+1e-6>=l['manhattan_lower_um']
    # Native M/S/T and every actual auxiliary macro keep all original passive
    # physical devices and all native RC/coupling records in the merged model.
    restored=restore_physical(native,out)
    prepared=out/'prepared';meta=prepare(native,prepared,inputs['links'])
    meta['native_verilog']=restored;meta['route_inputs']=inputs
    (prepared/'prepared.json').write_text(json.dumps(meta)+'\n')
    (out/'linkclose-prepare.json').write_text(json.dumps(dict(passed=True,pair=pair,
        route_source=str(routed),route_receipt_sha256=sha(routed/'receipt.json'),
        geometry=json.loads((out/'geometry.json').read_text()),links=len(inputs['links']),
        wire_length_um=dict(min=min(l['routed_length_um']for l in inputs['links']),max=max(l['routed_length_um']for l in inputs['links'])),
        scope='Actual complete signal route, preserved M10 landings, independent connectivity/short/width/spacing/enclosure checks; fixed native PG and separate acceptance retained. Shared clock root is ideal; new top supply/clock routing is outside experiment.'),indent=2)+'\n')


def coupon_model(base):
    rows=[]
    for rid,kind in [('912','short'),('912','long'),('912','via'),('918','dense'),('918','upper')]:
        folder=base/('block-v1-20261029-'+rid)/'tasks'/('linkclose-field-'+kind)
        d,r=bound(folder,'linkclose-field.json');assert d['passed'];rows.append(d)
    # A coupon-informed sensitivity range, not a proven upper bound on every
    # native occupancy, aggressor direction, environment or foundry variation.
    grounded=max((r['total_ff']+5*r['sigma_ff'])/r['length_um']for r in rows if r['kind']!='via')
    opposite=max((r['opposite_switching_miller_ff']+10*r['sigma_ff'])/r['length_um']for r in rows if r['kind']!='via')
    via=max(0.,rows[2]['total_ff']-rows[1]['total_ff'])/2+5*(rows[2]['sigma_ff']+rows[1]['sigma_ff'])
    return dict(grounded_ff_per_um=grounded,opposite_ff_per_um=opposite,via_ff=via,
        resistance_ohm_per_um=.015,via_resistance_ohm=.08,guard=1.2,
        coupon_totals=[dict(kind=r['kind'],length_um=r['length_um'],total_ff=r['total_ff'],ground_ff=r['ground_ff'],coupling_ff=r['coupling_ff'],sigma_ff=r['sigma_ff'])for r in rows],
        qualification='Coupon-informed research sensitivity envelope. Effective grounded capacitance approximates switching scenarios; no actual-layout Maxwell matrix, dynamic SI, foundry RCX, or general manufacturing upper bound is claimed.')


def measure(root,out,cpus,run,pair,variant):
    from interconnect_spef import canonical_maps,EXTRA_MAP,header,write_net,cell_pin,audit_native,wrapper
    from interconnect_experiment import sta_script,read_results
    assert cpus==16 and variant in ('grounded','opposite','guarded','length2','length4','load2','load4')
    prepared=out.parent/('linkclose-prepare-'+pair)
    prior,receipt=bound(prepared,'linkclose-prepare.json')
    meta_path=prepared/'prepared/prepared.json';assert sha(meta_path)==receipt['outputs']['prepared/prepared.json']
    meta=json.loads(meta_path.read_text());native=meta['route_inputs']['native']
    native={s:dict(r,verilog=meta['native_verilog'][s]['path'])for s,r in native.items()}
    model=coupon_model(out.parents[2]);maps=canonical_maps(meta,'direct')
    scale=2. if variant=='length2' else 4. if variant=='length4' else 1.
    load=2 if variant=='load2' else 4 if variant=='load4' else 1
    c=model['grounded_ff_per_um'] if variant=='grounded' else model['opposite_ff_per_um']
    guard=1. if variant in ('grounded','opposite') else model['guard'];c*=guard
    rows=[];observations=[];next_id=EXTRA_MAP+1
    for l in meta['links']:
        source=meta['selected'][':'.join(l['source'])];sink=meta['selected'][':'.join(l['sink'])]
        receivers=[sink]+[meta['selected'][':'.join(e)]for e in l.get('extra_sinks',[])]
        net_id=next_id;next_id+=1;maps[net_id]=l['id'];net='*'+str(net_id)
        nodes=sorted({tuple(e[k])for e in l['edges']for k in ('a','b')});ids={p:net+':'+str(i)for i,p in enumerate(nodes)}
        caps={p:0. for p in nodes};res=[]
        for e in l['edges']:
            a,b=tuple(e['a']),tuple(e['b']);length=e['length_um']*scale
            cap=(model['via_ff']*guard if e['via'] is not None else length*c)/1000
            resistance=(model['via_resistance_ohm'] if e['via'] is not None else length*model['resistance_ohm_per_um'])*guard
            assert resistance>0 and cap>=0
            caps[a]+=cap/2;caps[b]+=cap/2;res.append([ids[a],ids[b],str(resistance)])
        source_point=('metal10',*[round(x*2000)for x in l['source_xy_um']]);sink_point=('metal10',*[round(x*2000)for x in l['sink_xy_um']])
        res += [[source['internal_node'],ids[source_point],'0.000001'],[ids[sink_point],sink['internal_node'],'0.000001']]
        for receiver,xy in zip(receivers[1:],l.get('extra_sink_xy_um',[])):
            point=('metal10',*[round(x*2000)for x in xy])
            res.append([ids[point],receiver['internal_node'],'0.000001'])
        # Extra lumped boundary loading is labelled a load sensitivity test,
        # not physically duplicated receiver macros or certified fanout.
        extra_load_ff=float(Decimal(sink['native_cap'])*1000)*(load-1)
        caps[sink_point]+=extra_load_ff/1000
        caprows=[[ids[p],str(v)]for p,v in caps.items()if v>0]
        rows.append((net,[source]+receivers,[],caprows,res))
        drivers=[r[1]for r in source['conn']if r[0]=='*I' and r[2]=='O'];sinks=[r[1]for receiver in receivers for r in receiver['conn']if r[0]=='*I' and r[2]=='I']
        assert len(drivers)==1 and sinks
        observations.append(dict(**{k:v for k,v in l.items()if k!='edges'},source_driver=cell_pin(drivers[0],maps),first_native_loads=[cell_pin(p,maps)for p in sinks],new_wire_cap_ff=sum(caps.values())*1000,extra_load_ff=extra_load_ff,via_count=sum(e['via']is not None for e in l['edges']),wire_length_um=l['routed_length_um']*scale))
    with (out/'links.spef').open('w')as stream:
        stream.write(header(maps))
        for row in rows:write_net(stream,*row)
    common=prepared/'prepared/common-direct.spef';assert sha(common)==receipt['outputs']['prepared/common-direct.spef']
    proof=audit_native(meta,common,out/'links.spef')
    (out/'wrapper.v').write_text(wrapper(meta,native,'direct'))
    (out/'sta.tcl').write_text(sta_script(native,common,out,dict(links=observations)))
    run(['openroad','-no_init','-exit',out/'sta.tcl'],'sta.log')
    result=read_results(out,len(observations))
    report=dict(passed=True,experiment_completed=True,pair=pair,variant=variant,length_scale=scale,extra_native_wire_load_factor=load,
        model=model,observations=observations,native_preservation=proof,**result,
        geometry_source=str(prepared),source_receipt_sha256=sha(prepared/'receipt.json'),links_spef_sha256=sha(out/'links.spef'),
        production_macros_modified=False,
        scope='Complete actual macros plus their fixed auxiliary interfaces, native device/CTS/RC retained; actual routed centerline/via RC graph under coupon-informed grounded/opposite/guard scenarios. Length and extra-load cases are sensitivities on that graph, not newly routed layouts. Shared ideal clock root and externally constrained phase control remain assumptions. No generic safe fanout or manufacturing calibration claim.')
    (out/'linkclose-result.json').write_text(json.dumps(report,indent=2)+'\n')
