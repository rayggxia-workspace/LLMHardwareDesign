"""Actual finite two-net branching coupons using frozen T and real repeaters."""
import json
from pathlib import Path
import re
from interconnect_spef import sha


def route(root,out,cpus,run,key):
    from linkclose_route import definitions
    from overlay import generate
    match=re.fullmatch(r'([fb])(1|2|4)d(0|128|256|512|1024|1536|2048)',key)
    typ,count,gap=match.groups();count,gap=int(count),int(gap)
    assert cpus==16
    native,lefs,pins,size,_,_=definitions(root,out.parents[2],'ts',
        dict(bank='block-v1-20261029-914',booster='block-v1-20261029-916'))
    native={k:native[k]for k in ('t','booster')};lefs={k:lefs[k]for k in native}
    placements=dict(t=[1000,1000]);links=[];routes={};source_side='t'
    groups=[('read_data[0]','data','left'),('read_valid','valid','right')]
    if typ=='b':
        assert gap>=128
        native.pop('t');lefs.pop('t');source_side='driver'
        native['driver']=dict(native['booster']);lefs['driver']=lefs['booster'];pins['driver']=pins['booster'];size['driver']=size['booster']
        placements=dict(driver=[200,200]);groups=[('o','relay','right')]
    for port,role,side in groups:
        source=[pins[source_side][port][i]+placements[source_side][i] for i in (0,1)]
        sinks=[];sinkxy=[]
        x=1000-84-gap if side=='left' else 2040+20+gap
        if typ=='b':x=source[0]+gap-pins['booster']['i'][0]
        for i in range(count):
            name=role+str(i)
            native[name]=dict(native['booster']);lefs[name]=lefs['booster']
            pins[name]=pins['booster'];size[name]=size['booster']
            placements[name]=[x,source[1]-pins[name]['i'][1]+80*i]
            sinks.append([name,'i']);sinkxy.append([x+pins[name]['i'][0],source[1]+80*i])
        name='n%03d'%len(links)
        l=dict(id=name,source=[source_side,port],sink=sinks[0],extra_sinks=sinks[1:],role=role,
            source_xy_um=source,sink_xy_um=sinkxy[0],extra_sink_xy_um=sinkxy[1:],
            manhattan_lower_um=abs(source[0]-sinkxy[0][0])+80*(count-1))
        links.append(l)
        point=lambda xy:'( %d %d )'%tuple(round(v*2000)for v in xy)
        # Explicit channel route, not a synthetic wire-length substitution.
        # Every branch terminates in a placed, separately accepted64um macro.
        text='metal10 '+point(source)+' BV1_via10 NEW metal11 '+point(source)+' '+point(sinkxy[0])
        text+=' NEW metal10 '+point(sinkxy[0])+' BV1_via10'
        if count>1:
            text+=' NEW metal11 '+point(sinkxy[0])+' BV1_via11 NEW metal12 '+point(sinkxy[0])+' '+point(sinkxy[-1])
            for xy in sinkxy[1:]:
                text+=' NEW metal11 '+point(xy)+' BV1_via11 NEW metal10 '+point(xy)+' BV1_via10'
        routes[name]=text
    del native['booster'];del lefs['booster']
    size={k:size[k]for k in native};pins={k:pins[k]for k in native}
    upper=[max(p[i]+size[k][i]for k,p in placements.items())+100 for i in (0,1)]
    for i,(a,p)in enumerate(placements.items()):
        for b,q in list(placements.items())[:i]:
            assert p[0]+size[a][0]<=q[0] or q[0]+size[b][0]<=p[0] or p[1]+size[a][1]<=q[1] or q[1]+size[b][1]<=p[1]
    spec=json.loads((root/'project/experiments/block_v1/technology-2um-v1.json').read_text())
    generate(Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef'),spec,out/'technology')
    text='VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\nDESIGN fanout_'+key+' ;\nUNITS DISTANCE MICRONS 2000 ;\nDIEAREA ( 0 0 ) ( %d %d ) ;\n'%tuple(round(v*2000)for v in upper)
    text+='COMPONENTS %d ;\n'%len(native)
    for k,row in native.items():text+='- u_'+k+' '+row['top']+' + FIXED '+point(placements[k])+' N ;\n'
    text+='END COMPONENTS\nNETS %d ;\n'%len(links)
    for l in links:
        terms=[l['source'],l['sink']]+l['extra_sinks']
        text+='- '+l['id']+' '+' '.join('( u_'+a+' '+p+' )'for a,p in terms)+' + USE SIGNAL + ROUTED '+routes[l['id']]+' ;\n'
    text+='END NETS\nEND DESIGN\n';(out/'input.def').write_text(text)
    request=dict(native=native,lefs={k:dict(path=str(v),sha256=sha(v))for k,v in lefs.items()},pins=pins,size=size,placements=placements,links=links,die_um=upper,fanout=count,additional_gap_um=gap)
    (out/'route-inputs.json').write_text(json.dumps(request,indent=2)+'\n')
    script='set_thread_count 16\nread_lef {'+str(out/'technology/research12.tech.lef')+'}\n'
    for i,lef in enumerate(dict.fromkeys(lefs.values())):
        p=out/('macro-%d.lef'%i);p.write_bytes(lef.read_bytes());assert sha(p)==sha(lef)
        script+='read_lef {'+str(p)+'}\n'
    script+='read_def {'+str(out/'input.def')+'}\nwrite_db routed.odb\nwrite_def routed.def\nsource {'+str(root/'project/experiments/block_v1/odb_geometry.tcl')+'}\nbvgeom::export geometry.tsv\n'
    (out/'route.tcl').write_text(script);run(['openroad','-no_init','-exit',out/'route.tcl'],'route.log')
    (out/'linkclose-route.json').write_text(json.dumps(dict(passed=True,pair=key,links=len(links),fanout=count,
        inputs_sha256=sha(out/'route-inputs.json'),odb_sha256=sha(out/'routed.odb'),def_sha256=sha(out/'routed.def'),geometry_sha256=sha(out/'geometry.tsv'),
        scope='Explicitly routed actual data/valid fanout coupon with all active receiver footprints nonoverlapping and frozen; independent research geometry/native RC/STA reception remains separate. No automatic router claim.'),indent=2)+'\n')
