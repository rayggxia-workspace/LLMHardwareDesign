"""Create a NEW frozen parent baseline from the verified three-leaf graph.

This does not reconstruct historical handoffs. User authorized supplementing
missing materials on 2026-10-27. Port-only Liberty is for routing/linking only;
it is deliberately unqualified for STA, load, slew, power or functional claims.
"""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,csv,gzip,hashlib,json,math
from inventory import load,owner,pin_names

def quoted(value):
    assert not any(c in str(value) for c in '{}\\\n\r'),value
    return '{'+str(value)+'}'

def escaped(name):
    assert not any(c.isspace() for c in name) and '\\' not in name,name
    return '\\'+name+' '

def write_json(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def prepare(root,out,design,focus):
    root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    graph=load(root/'partition-r02'/(design+'_partition_graph.json.gz'));top=graph['top_module']
    records={};masters={};dims={};physical={};parents=defaultdict(list)
    for inst,cell in top['cells'].items():
        case=owner(inst,design);m=load(root/(case+'.meta.json'));units=m['units_per_micron']
        die=[v/units for v in m['die_dbu']];assert die[:2]==[0,0]
        dims[case]=die[2:]
        if 'design' in m:master=m['design']
        else:
            with gzip.open(root/'physical'/case/'design.tsv.gz','rt') as f:master=dict(line.rstrip().split('\t',1) for line in f)['design']
        masters[case]=master
        with (root/(case+'_pin_coordinates.csv')).open(encoding='utf-8-sig') as f:
            pins={r['pin']:r for r in csv.DictReader(f) if r['plan']=='A'}
        physical[case]=pins
        module=graph['frontier'][cell['type']];expected={}
        for port,p in module['ports'].items():
            for pin,bit in zip(pin_names(port,p),cell['connections'][port]):
                assert isinstance(bit,int),'A literal is not a shared physical net; handle separately, never merge zeros'
                expected[pin]=(p['direction'],bit)
                parents[bit].append({'kind':'ITERM','instance':inst,'case':case,'pin':pin,'direction':p['direction'],'original_leaf_pin_layer':pins[pin]['layer']})
        assert set(pins)==set(expected)
        assert all(pins[p]['direction'].lower()==d for p,(d,b) in expected.items())
        assert not any(p.get('upto',0) for p in module['ports'].values()),'Ascending port requires an explicit bit-order implementation'
        records[case]={'instance':inst,'master':master,'pins':expected,
          'ports':{n:{'direction':p['direction'],'width':len(p['bits']),'offset':p.get('offset',0),'connections_lsb_first':cell['connections'][n]} for n,p in module['ports'].items()}}
    assert focus in records
    external=[];constant_drivers=[]
    next_constant=max([b for c in top['cells'].values() for bs in c['connections'].values() for b in bs if isinstance(b,int)]+[b for p in top['ports'].values() for b in p['bits'] if isinstance(b,int)])+1
    for port,p in top['ports'].items():
        for bit_index,(pin,bit) in enumerate(zip(pin_names(port,p),p['bits'])):
            literal=None
            if isinstance(bit,str):
                assert bit in ['0','1'] and p['direction']=='output',(pin,bit,'not a routable known constant output')
                literal=bit;bit=next_constant;next_constant+=1
                driver={'instance':'top_constant_'+str(len(constant_drivers)),'master':'LOGIC'+literal+'_X1','pin':'Z','value':literal,'bit':bit,'external_pin':pin}
                constant_drivers.append(driver)
                parents[bit].append({'kind':'ITERM','instance':driver['instance'],'case':'TOP_CONSTANT_INFRASTRUCTURE','pin':'Z','direction':'output','original_leaf_pin_layer':'metal1','literal_value':literal,'new_constant_driver':True})
            external.append({'pin':pin,'direction':p['direction'],'bit':bit,'original_literal':literal,'port':port,'port_width':len(p['bits']),'port_index':p.get('offset',0)+bit_index})
            parents[bit].append({'kind':'BTERM','pin':pin,'direction':p['direction']})
    # Freeze a common R0 two-row floorplan, with 80um margins and channel.
    aux=design+'_aux';compute=[c for c in records if c!=aux];assert len(compute)==2
    compute.sort(key=lambda c:0 if c in ['act','gemm'] else 1)
    channel=80.0
    # Actual platform M5/M6 routing pitch is 0.28um. Preserve the source track
    # phase when translating each unchanged R0 macro, rather than shifting by
    # an arbitrary 80um and making original edge ports spuriously off-track.
    snap=lambda v:round(math.ceil((v-1e-9)/.28)*.28,6)
    margin=snap(80.0);positions={aux:[margin,margin]};x=margin;y=snap(margin+dims[aux][1]+channel)
    for c in compute:positions[c]=[x,y];x=snap(x+dims[c][0]+channel)
    width=math.ceil((max(positions[c][0]+dims[c][0] for c in records)+margin)/.005-1e-8)*.005
    height=math.ceil((max(positions[c][1]+dims[c][1] for c in records)+margin)/.005-1e-8)*.005
    # External layers are NEW policy: use the most frequent real peer layer.
    # This creates no claim about absent historical TOP_IO/handoff layers.
    buckets=defaultdict(list)
    for e in external:
        peers=[r for r in parents[e['bit']] if r['kind']=='ITERM']
        layers=Counter(r['original_leaf_pin_layer'] for r in peers)
        e['layer']=(sorted(layers,key=lambda k:(-layers[k],k))[0] if layers else 'metal5')
        if e['original_literal'] is not None:e['layer']='metal5'
        assert e['layer'] in ['metal5','metal6']
        e['layer_evidence']='NEW controlled boundary policy, majority actual leaf peer layer; constant/unused TOP_IO uses declared M5 policy. Not historical.'
        e['unused_declared_top_pin_no_physical_leaf_peer']=not bool(peers)
        buckets[e['layer']].append(e)
    for layer,entries in buckets.items():
        vertical=layer=='metal5';length=height if vertical else width
        per_side=math.ceil(len(entries)/2);pitch=1.12
        assert (per_side+1)*pitch<length-40,(design,layer,'new boundary insufficient; do not silently compress pitch')
        for i,e in enumerate(entries):
            track_offset=.07 if vertical else .095
            offset=track_offset+math.ceil((20-track_offset)/.28)*.28+(i//2)*pitch
            e['xy_um']=([.07 if i%2==0 else width-.07,offset] if vertical else [offset,.07 if i%2==0 else height-.07])
            e['size_um']=[.14,.14]
    topname='hpy_pinxy_'+design+'_controlled_parent'
    # Preserve actual vector ports. Literal escaped scalar names such as
    # \\data[0] do NOT reliably bind a Liberty/LEF bus bit in this OpenROAD.
    verilog=['// NEW controlled parent; exact frozen frontier graph, no new functional logic.',
       'module '+topname+'('+', '.join(escaped(n) for n in top['ports'])+');']
    for name,p in top['ports'].items():
        assert not p.get('upto',0)
        n=len(p['bits']);offset=p.get('offset',0)
        verilog.append(p['direction']+' '+(f'[{offset+n-1}:{offset}] ' if n>1 else '')+escaped(name)+';')
    verilog += ['wire n_'+str(bit)+';' for bit in sorted(parents)]
    for e in external:
        assert e['direction'] in ['input','output']
        portref=escaped(e['port'])+(f'[{e["port_index"]}]' if e['port_width']>1 else '')
        verilog.append('assign '+('n_'+str(e['bit'])+' = '+portref if e['direction']=='input' else portref+' = n_'+str(e['bit']))+';')
    for case,rec in records.items():
        ports=[]
        for name,p in rec['ports'].items():
            bits=p['connections_lsb_first'];expression=('{' + ','.join('n_'+str(bit) for bit in reversed(bits))+'}') if len(bits)>1 else 'n_'+str(bits[0])
            ports.append('.'+escaped(name)+'('+expression+')')
        verilog.append('p126_'+case+'_A '+escaped(rec['instance'])+'('+', '.join(ports)+');')
    for driver in constant_drivers:
        verilog.append(driver['master']+' '+driver['instance']+'(.Z(n_'+str(driver['bit'])+'));')
    verilog.append('endmodule');(out/'parent.v').write_text('\n'.join(verilog)+'\n',encoding='utf-8')
    lib=['/* ROUTING/LINKING PORT STUBS ONLY. NOT CHARACTERIZED TIMING MODELS. */',
      'library (pinxy_ROUTING_ONLY) { delay_model : table_lookup; bus_naming_style : "%s[%d]"; time_unit : "1ns"; voltage_unit : "1V"; current_unit : "1mA"; pulling_resistance_unit : "1kohm"; capacitive_load_unit (1,pf); nom_voltage : 1.0; nom_temperature : 25; nom_process : 1;']
    types=sorted({(p['width'],p['offset']) for r in records.values() for p in r['ports'].values() if p['width']>1})
    for n,offset in types:
        lib.append(f'type (B{n}_{offset}) {{ base_type : array; data_type : bit; bit_width : {n}; bit_from : {offset+n-1}; bit_to : {offset}; downto : true; }}')
    for case,rec in records.items():
        for view in ['A','A_child_replay','Aopt','B','C']:
            lib.append('cell ("p126_'+case+'_'+view+'") { is_macro_cell : true; area : '+str(dims[case][0]*dims[case][1])+';')
            for name,p in rec['ports'].items():
                assert '"' not in name;direction=p['direction'];n=p['width'];offset=p['offset']
                attrs='direction : '+direction+'; '+('capacitance : 0; ' if direction=='input' else '')+('clock : true; ' if name=='clk' else '')
                if n==1:lib.append('pin ("'+name+'") { '+attrs+'}')
                else:lib.append(f'bus ("{name}") {{ bus_type : B{n}_{offset}; direction : {direction}; pin ("{name}[{offset+n-1}:{offset}]") {{ {attrs} }} }}')
            lib += ['pg_pin (VDD) { pg_type : primary_power; voltage_name : VDD; }','pg_pin (VSS) { pg_type : primary_ground; voltage_name : VSS; }','}']
    lib.append('}');(out/'routing_only.lib').write_text('\n'.join(lib)+'\n',encoding='utf-8')
    setup=[f'initialize_floorplan -die_area {{0 0 {width:.6f} {height:.6f}}} -core_area {{10 10 {width-10:.6f} {height-10:.6f}}} -site FreePDK45_38x28_10R_NP_162NW_34O',
      'source /OpenROAD-flow-scripts/flow/platforms/nangate45/make_tracks.tcl']
    for case,rec in records.items():
        x,y=positions[case];setup.append('place_macro -macro_name '+quoted(rec['instance'])+f' -location {{{x:.6f} {y:.6f}}} -orientation R0 -exact')
    if constant_drivers:
        setup += ['set b [ord::get_db_block]','set row [lindex [$b getRows] 0]','lassign [$row getOrigin] tie_x tie_y','set tie_site [[$row getSite] getWidth]']
        for driver in constant_drivers:
            setup += ['set i [$b findInst '+driver['instance']+']','$i setOrient [$row getOrient]','$i setLocation $tie_x $tie_y','$i setPlacementStatus FIRM','set tie_x [expr {$tie_x+[[$i getMaster] getWidth]+$tie_site}]']
    setup += ['foreach i [[ord::get_db_block] getInsts] {$i setPlacementStatus FIRM}']
    for e in external:
        x,y=e['xy_um'];setup.append('place_pin -pin_name '+quoted(e['pin'])+' -layer '+e['layer']+f' -location {{{x:.6f} {y:.6f}}} -pin_size {{0.14 0.14}}')
    (out/'setup.tcl').write_text('\n'.join(setup)+'\n',encoding='utf-8')
    expected=[]
    for bit,terms in parents.items():
        for t in terms:expected.append({'parent_bit':bit,**t})
    write_json(out/'endpoints.json',expected)
    contract={'scope':'NEW_CONTROLLED_PARENT_NOT_HISTORICAL','user_authorization':'2026-10-27: no additional materials; supplement necessary missing materials autonomously',
      'historical_parent_handoff_layers':'UNKNOWN_UNCHANGED_IN_ORIGINAL_DATA','design':design,'focus':focus,'top':topname,
      'source_partition_sha256':graph['source_partition_sha256'],'physical_instances':records,'die_um':[0,0,width,height],
      'placements_R0_um':positions,'leaf_dimensions_um':dims,'external_pins':external,'endpoint_count':len(expected),'parent_bits':len(parents),
      'signal_routing_policy':'NEW frozen metal2-metal10; clock metal4-metal10; not a claim about missing original parent policy',
      'pin_target_policy':'Every ITerm retains its original verified leaf pin layer; TOP_IO layer policy separately declared. Same endpoint graph and layer contract across all parent variants.',
      'PDN_policy':'NEW M1/M4/M7/M10 parent grid for constant cells and M7-to-M10 macro PG access, reusing Issue15 strategy. Freeze actual A geometry and reuse across variants; preserve every original leaf PG view. Check PDN and native DRC separately.',
      'macro_timing_model':'UNCHARACTERIZED_ROUTING_ONLY_STUB; NO PARENT STA/ELECTRICAL QUALIFICATION',
      'new_parent_constant_drivers':constant_drivers,'constant_driver_policy':'Distinct physical drivers for distinct declared constant TOP outputs; do not merge all zero literals. New infrastructure retained identically across A/A_replay/Aopt/B/C, not hidden XY benefit.',
      'added_parent_constant_cells':len(constant_drivers),'added_sequential_or_buffer_cells':0,'changed_logic_function_protocol_state_storage':False,'full_GDS_LVS':'NOT_QUALIFIED; SRAM physical device views missing, no allow-empty qualification'}
    write_json(out/'contract.json',contract)
    write_json(out/'input_hashes.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()})
    print('NEW_CONTROLLED_PARENT_INPUTS',design,focus,3,'physical instances',len(expected),'signal endpoints')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',required=True);p.add_argument('--design',choices=['opentpu','llaccel'],required=True);p.add_argument('--focus',required=True);a=p.parse_args();prepare(a.root,a.out,a.design,a.focus)
