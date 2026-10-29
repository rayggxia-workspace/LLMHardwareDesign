"""Route complete representative buses only on the two custom metal layers."""
import json
from pathlib import Path
from interconnect_spef import sha

ACCEPT_RUNS=dict(bank='block-v1-20261029-921',bridge='block-v1-20261029-921',booster='block-v1-20261029-916')


def definitions(root,base,pair,accept_runs=None):
    accept_runs=ACCEPT_RUNS if accept_runs is None else accept_runs
    source=json.loads((root/'project/experiments/block_v1/interconnect-sources.json').read_text())['macros']
    deliveries=json.loads((root/'project/experiments/block_v1/revision300-deliveries.json').read_text())
    native={};lefs={};pins={};size={}
    for kind in pair:
        row=source[kind];p=Path(row['verilog']);assert sha(p)==row['hashes']['6_final.v']
        native[kind]=dict(row)
        geometry=base/deliveries['geometry'][kind];r=json.loads((geometry/'receipt.json').read_text());assert r['passed']
        lef=geometry/'candidate.lef';assert sha(lef)==r['outputs'][lef.name];lefs[kind]=lef
        # Native pins from the exact accepted final source, not a synthetic pad.
        actual=base/'block-v1-20261029-910/tasks/linkclose-probe'/(kind+'-pins.tsv')
        probe=json.loads((actual.parent/'receipt.json').read_text());assert probe['passed']
        assert sha(actual)==probe['outputs'][actual.name]
        pins[kind]={}
        for line in actual.read_text().splitlines():
            name,direction,layer,*box=line.split('\t');a,b,c,d=map(int,box)
            assert layer=='metal10';pins[kind][name]=[(a+c)/4000,(b+d)/4000]
        size[kind]=row['die_um']
    kinds=('bridge','booster') if pair=='mt' else ('bank','booster')
    for kind in kinds:
        accepted=base/accept_runs[kind]/'tasks'/('linkclose-accept-'+kind)
        r=json.loads((accepted/'receipt.json').read_text());assert r['passed']
        report=accepted/'linkclose-accept.json';assert sha(report)==r['outputs'][report.name]
        d=json.loads(report.read_text());assert d['passed']
        folder=Path(d['source']);raw=json.loads((folder/'linkclose-physical.json').read_text())
        native[kind]=dict(top=raw['top'],verilog=raw['files']['6_final.v']['path'],
            spef=raw['files']['6_final.spef']['path'],sdc=str(folder/'input.sdc'),hashes={n:row['sha256']for n,row in raw['files'].items()},
            physical_receipt_path=str(accepted/'receipt.json'),physical_receipt_sha256=sha(accepted/'receipt.json'))
        lefs[kind]=accepted/'candidate.lef';assert sha(lefs[kind])==r['outputs']['candidate.lef']
        pins[kind]={p['pin']:p['xy_um'] for p in json.loads((folder/'pins.json').read_text())['pins']}
        size[kind]=raw['die_um']
    native['return']=dict(native['booster']);lefs['return']=lefs['booster']
    pins['return']=pins['booster'];size['return']=size['booster']
    if pair=='mt':
        # Buffer input landings align with M result fields; all auxiliary active
        # cells occupy separately charged, non-overlapping prefab footprints.
        placements=dict(m=[200,400],bridge=[200,220],t=[1020,400],booster=[2080,728],**{'return':[948,500]})
        links=[]
        def add(a,ap,b,bp,role):links.append(dict(id='n%03d'%len(links),source=[a,ap],sink=[b,bp],role=role))
        for bit in range(128):add('m','rsp_data[%d]'%bit,'bridge','response_data[%d]'%bit,'data')
        for ap,bp in [('rsp_valid','response_valid'),('rsp_error','response_error'),('rsp_saturated','response_saturated'),('cmd_ready','command_ready')]:add('m',ap,'bridge',bp,'control')
        add('bridge','response_ready','m','rsp_ready','ready')
        for bit in range(128):add('bridge','write_data[%d]'%bit,'t','write_data[%d]'%bit,'data')
        add('bridge','write_valid','t','write_valid','valid')
        for bit in range(10):add('bridge','write_index[%d]'%bit,'t','write_index[%d]'%bit,'address')
        add('t','write_ready','booster','i','ready');add('booster','o','return','i','ready');add('return','o','bridge','write_ready','ready')
    else:
        placements=dict(t=[200,200],bank=[200,1260],s=[200,1480],booster=[116,2000],**{'return':[116,352]})
        links=[]
        def add(a,ap,b,bp,role):links.append(dict(id='n%03d'%len(links),source=[a,ap],sink=[b,bp],role=role))
        for bit in range(128):
            add('t','read_data[%d]'%bit,'bank','i[%d]'%bit,'data')
            add('bank','o[%d]'%bit,'s','din[%d]'%bit,'data')
        for bit in range(10):
            add('t','read_index[%d]'%bit,'bank','i[%d]'%(128+bit),'address')
            add('bank','o[%d]'%(128+bit),'s','addr[%d]'%bit,'address')
        add('t','read_valid','bank','i[138]','valid');add('bank','o[138]','s','req','valid')
        add('s','ready','booster','i','ready');add('booster','o','return','i','ready');add('return','o','t','read_take','ready')
    for i,(a,p) in enumerate(placements.items()):
        for b,q in list(placements.items())[:i]:
            assert p[0]+size[a][0]<=q[0] or q[0]+size[b][0]<=p[0] or p[1]+size[a][1]<=q[1] or q[1]+size[b][1]<=p[1],('Active footprints overlap',a,b)
    return native,lefs,pins,size,placements,links


def route(root,out,cpus,run,pair,representative=False):
    from overlay import generate
    assert cpus==16 and pair in ('mt','ts')
    base=out.parents[2]
    native,lefs,pins,size,placements,links=definitions(root,base,pair)
    original_count=len(links)
    if representative:
        def keep(link):
            for _,port in (link['source'],link['sink']):
                import re
                m=re.search(r'\[(\d+)\]',port)
                if m and int(m[1])not in (0,9,127,128,137,138):return False
            return True
        links=[l for l in links if keep(l)]
    tech=json.loads((root/'project/experiments/block_v1/technology-2um-v1.json').read_text())
    generate(Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef'),tech,out/'technology')
    upper=[max(p[i]+size[k][i] for k,p in placements.items())+200 for i in (0,1)]
    text='VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\nDESIGN linkclose_'+pair+' ;\nUNITS DISTANCE MICRONS 2000 ;\n'
    text+='DIEAREA ( 0 0 ) ( %d %d ) ;\n'%tuple(round(v*2000) for v in upper)
    text+='COMPONENTS %d ;\n'%len(native)
    for k,row in native.items():text+='- u_'+k+' '+row['top']+' + FIXED ( %d %d ) N ;\n'%tuple(round(v*2000)for v in placements[k])
    text+='END COMPONENTS\nNETS %d ;\n'%len(links)
    for link in links:
        a,ap=link['source'];b,bp=link['sink']
        text+='- '+link['id']+' ( u_'+a+' '+ap+' ) ( u_'+b+' '+bp+' ) + USE SIGNAL ;\n'
        link['source_xy_um']=[pins[a][ap][i]+placements[a][i]for i in (0,1)]
        link['sink_xy_um']=[pins[b][bp][i]+placements[b][i]for i in (0,1)]
        link['manhattan_lower_um']=sum(abs(link['source_xy_um'][i]-link['sink_xy_um'][i])for i in (0,1))
    text+='END NETS\nSPECIALNETS 2 ;\n'
    for net in ('VDD','VSS'):text+='- '+net+' '+' '.join('( u_'+k+' '+net+' )'for k in native)+' + USE '+('POWER'if net=='VDD' else 'GROUND')+' ;\n'
    text+='END SPECIALNETS\nEND DESIGN\n';(out/'input.def').write_text(text)
    request=dict(native=native,lefs={k:dict(path=str(v),sha256=sha(v))for k,v in lefs.items()},pins=pins,size=size,placements=placements,links=links,die_um=upper,representative_subset=representative,original_full_bus_links=original_count)
    (out/'route-inputs.json').write_text(json.dumps(request,indent=2)+'\n')
    # Finite experiment supplies coarse 32um routing corridors explicitly.
    # FastRoute's native M3-sized GCells under-resolve the 4um upper tracks
    # (GRT-0228 in run917). This is a guide input, not fabricated wire: Triton
    # detailed routing still chooses actual tracks/vias and enforces the exact
    # unmodified custom geometry rules; separate checks receive its result.
    import math
    guides=''
    for link in links:
        a,b=link['source_xy_um'],link['sink_xy_um']
        box=[max(0,math.floor((min(a[i],b[i])-32)/32)*32)for i in (0,1)]
        box += [min(upper[i],math.ceil((max(a[i],b[i])+32)/32)*32)for i in (0,1)]
        # Guide coordinates are database units, unlike LEF/track Tcl microns.
        guides+=link['id']+'\n(\n'+''.join(' '.join(str(round(v*2000))for v in box)+' metal%d\n'%level for level in (11,12))+')\n'
    (out/'route.guide').write_text(guides)
    script='set_thread_count 16\nread_lef {'+str(out/'technology/research12.tech.lef')+'}\n'
    # OpenDB derives the library name from the LEF filename. Independent
    # accepted macros all export candidate.lef; unique byte-identical copies
    # prevent a duplicate-library name from discarding later macros.
    for i,lef in enumerate(dict.fromkeys(lefs.values())):
        copy=out/('macro-%d.lef'%i);copy.write_bytes(lef.read_bytes());assert sha(copy)==sha(lef)
        script+='read_lef {'+str(copy)+'}\n'
    script+='read_def {'+str(out/'input.def')+'}\nsource /OpenROAD-flow-scripts/flow/platforms/nangate45/make_tracks.tcl\nsource {'+str(out/'technology/new_tracks.tcl')+'}\n'
    script+='set_routing_layers -signal metal11-metal12\nset_macro_extension 0\n'
    script+='read_guides route.guide\n'
    script+='set grid [[ord::get_db_block] getGCellGrid]\n$grid resetGrid\n'
    script+='$grid addGridPatternX 0 %d 16000\n$grid addGridPatternY 0 %d 16000\n'%(math.ceil(upper[0]/8)+1,math.ceil(upper[1]/8)+1)
    script+='detailed_route -output_drc route-drc.rpt -output_guide_coverage coverage.csv -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 -via_access_layer metal10 -droute_end_iter 64 -drc_report_iter_step 5 -verbose 1\n'
    script+='write_db routed.odb\nwrite_def routed.def\nsource {'+str(root/'project/experiments/block_v1/odb_geometry.tcl')+'}\nbvgeom::export geometry.tsv\n'
    (out/'route.tcl').write_text(script)
    run(['openroad','-no_init','-exit',out/'route.tcl'],'route.log')
    assert not (out/'route-drc.rpt').read_text().strip(),'Custom12 native router DRC is nonzero'
    report=dict(passed=True,pair=pair,links=len(links),inputs_sha256=sha(out/'route-inputs.json'),
        odb_sha256=sha(out/'routed.odb'),def_sha256=sha(out/'routed.def'),geometry_sha256=sha(out/'geometry.tsv'),
        guide_method='Explicit32um coarse corridors after native global router GCell under-resolution; real TritonRoute detailed tracks/vias, not synthetic wiring.',
        scope='Actual complete representative bus route in M11/M12; independent geometry, native landing preservation and real-route RC/STA must still receive this result.')
    (out/'linkclose-route.json').write_text(json.dumps(report,indent=2)+'\n')
