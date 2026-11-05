"""Explicit fixed Link8 instances; no active logic in the custom upper layers.

The original native macro pins and RTL stay intact. Every inserted payload
path is recorded and independently contracted back to the exact original
topology. Link8 owns one reset-isolation bit, not a payload pipeline register.
"""
import copy,re


def xy(pin):
    if 'xy_um' in pin:return pin['xy_um']
    box=pin['box_dbu'];return[(box[0]+box[2])/4000,(box[1]+box[3])/4000]


def insert(module,manifest,pins,sources,fanout_ports=(),local_reset_padding=False,reference_group_counts=None,balanced_reset_banks=False):
    original=copy.deepcopy(module);cells=module['cells']
    from r256_scene import is_r256,validate_base
    r256=is_r256({n:c['type']for n,c in cells.items()})
    assert not local_reset_padding or r256
    assert reference_group_counts is None or(r256 and local_reset_padding and manifest['leaves']['control_s_arbiter_r7']['die_um']==[3200,3200])
    assert not balanced_reset_banks or reference_group_counts is not None
    if r256:validate_base({n:c['type']for n,c in cells.items()},set(manifest['leaves'])-{'control_link8'})
    else:assert len(cells)==26 and len(manifest['leaves'])==21
    assert 'control_link8' in manifest['leaves']
    all_bits={bit for cell in cells.values()for bits in cell['connections'].values()for bit in bits}
    all_bits.update(bit for port in module['ports'].values()for bit in port['bits'])
    assert all(isinstance(bit,int)for bit in all_bits)
    next_bit=max(all_bits)+1
    def allocate():
        nonlocal next_bit
        bit=next_bit;next_bit+=1;return bit
    # Exact receiving pin positions distinguish replicated fanout branches.
    sinks={}
    for name,c in original['cells'].items():
        for port,bits in c['connections'].items():
            if c['port_directions'][port]=='input':
                for index,bit in enumerate(bits):sinks.setdefault(bit,[]).append((name,port,index))
    for name,port in original['ports'].items():
        if port['direction']=='output':
            for index,bit in enumerate(port['bits']):sinks.setdefault(bit,[]).append(('TOP',name,index))
    split={}
    for item in fanout_ports:
        source,port=item.split(':');assert (source,port)in [('s_port','dout'),('controller','task_data'),('controller','task_last')]
        split.setdefault(source,set()).add(port)
    assert len(set(sources))==len(sources)and not set(sources)&set(split)
    rows=[];replacement={};reverse={}
    for source in list(sources)+sorted(split):
        assert source in ({'macro_s','macro_1','macro_2','macro_3','macro_4','macro_t'}|({'macro_r'}if r256 else set()))or source in split
        cell=cells[source];assert cell['port_directions']['clk']=='input' and cell['port_directions']['reset']=='input'
        clock=cell['connections']['clk'];reset=cell['connections']['reset'];assert len(clock)==len(reset)==1
        w,h=manifest['leaves'][cell['type']]['die_um'];groups={}
        for port,bits in cell['connections'].items():
            if cell['port_directions'][port]!='output' or(source in split and port not in split[source]):continue
            for index,bit in enumerate(bits):
                if bit not in sinks:continue
                pin=port+'['+str(index)+']'if port+'['+str(index)+']'in pins[cell['type']]else port
                x,y=xy(pins[cell['type']][pin]);assert 0<=x<=w and 0<=y<=h
                side=min(range(4),key=lambda s:[x,w-x,y,h-y][s])
                targets={}
                for target in sinks[bit]:targets.setdefault(target[0]if source in split else'ALL',[]).append(target)
                for destination,receivers in targets.items():
                    groups.setdefault((side,destination),[]).append((y if side<2 else x,pin,bit,receivers))
        assert groups
        serial=0;chunks=[]
        for(side,destination),group in sorted(groups.items()):
            group.sort()
            for offset in range(0,len(group),8):
                chunks.append((side,destination,group[offset:offset+8]))
        if reference_group_counts is not None:
            from current_pin_groups import balance
            chunks=balance(source,chunks,reference_group_counts)
        for side,destination,chunk in chunks:
                name='link_'+source+'_'+str(serial);serial+=1
                assert name not in cells
                inputs=[row[2]for row in chunk];inputs+=inputs[:1]*(8-len(inputs))
                outputs=[allocate()for _ in range(8)]
                cells[name]=dict(hide_name=0,type='control_link8',parameters={},attributes={},
                    port_directions=dict(clk='input',reset='input',in_data='input',out_data='output'),
                    connections=dict(clk=clock[:],reset=reset[:],in_data=inputs,out_data=outputs))
                lanes=[]
                for lane,(_,pin,old,receivers)in enumerate(chunk):
                    reverse[outputs[lane]]=old
                    for target in receivers:
                        assert target not in replacement;replacement[target]=outputs[lane]
                    lanes.append(dict(lane=lane,source_pin=pin,input_bit=old,output_bit=outputs[lane],
                        receiving_pins=[dict(instance=n,port=p,index=i)for n,p,i in receivers]))
                rows.append(dict(instance=name,source_instance=source,side=side,lanes=lanes,
                    fanout_branch=destination,padded_input_lanes=8-len(chunk),clock_bit=clock[0],reset_bit=reset[0],
                    state_owner=name,state_bits=1,payload_register_bits=0))
                if reference_group_counts is not None:
                    points=[xy(pins[cell['type']][lane['source_pin']])for lane in lanes]
                    rows[-1].update(source_pin_anchor_um=[sum(point[axis]for point in points)/len(points)for axis in (0,1)],source_pin_die_um=[w,h])
    for name,cell in original['cells'].items():
        for port,bits in cell['connections'].items():
            if cell['port_directions'][port]=='input':
                cells[name]['connections'][port]=[replacement.get((name,port,index),bit)for index,bit in enumerate(bits)]
    for port,row in module['ports'].items():
        if row['direction']=='output':row['bits']=[replacement.get(('TOP',port,index),bit)for index,bit in enumerate(row['bits'])]
    reset_banks=None
    if r256:
        from reset_link_banks import assign
        reset_banks=assign(module,rows,spatial_source_groups=reference_group_counts is not None,balanced_source_groups=balanced_reset_banks)
    if local_reset_padding:
        # Unconsumed output lanes need no payload source. Use the existing
        # local fixed reset driver; its added pin load is physically real and
        # must be included in all new placement/RC/STA evidence.
        consumers={b for p in module['ports'].values()if p['direction']=='output'for b in p['bits']}
        consumers.update(b for c in cells.values()for p,bs in c['connections'].items()if c['port_directions'][p]=='input'for b in bs)
        for row in rows:
            link=cells[row['instance']]['connections'];n=len(row['lanes'])
            unused=link['out_data'][n:];assert len(unused)==row['padded_input_lanes']
            assert not set(unused)&consumers,'Padding output is consumed'
            assert link['in_data'][:n]==[r['input_bit']for r in row['lanes']]
            link['in_data'][n:]=link['reset']*len(unused)
            row.update(padding_input_bit=link['reset'][0],unused_output_bits=unused)
        reset_banks['unused_lane_padding']='local-reset-unused-lanes/1'
    # Contract every branch independently and compare the whole original
    # module, including all data, control, fanout and host port connections.
    contracted=copy.deepcopy(module)
    for row in rows:del contracted['cells'][row['instance']]
    for cell in contracted['cells'].values():
        for port,bits in cell['connections'].items():cell['connections'][port]=[reverse.get(bit,bit)for bit in bits]
    for port in contracted['ports'].values():port['bits']=[reverse.get(bit,bit)for bit in port['bits']]
    assert contracted==original,'Fixed-link contraction changes original topology'
    return dict(schema='explicit-fixed-native-links/1',original_instance_count=29 if r256 else 26,links=rows,
        new_state_bits=len(rows),payload_register_bits=0,original_topology_exact_contraction=True,
        reset_banks=reset_banks,
        reset_contract='Link8 uses an independent same-state/same-cycle fixed reset53 branch in R256; legacy uses its source branch. Payload isolated during reset, enabled on first following clock. No new payload cycle.',
        original_macro_rtl_and_native_geometry_unchanged=True)


def validate(manifest,graph):
    instances=graph['instances'];base={k:v for k,v in instances.items()if v!='control_link8'}
    from r256_scene import is_r256,validate_base,SCHEMA
    r256=is_r256(instances)
    if r256:
        validate_base(instances,manifest['leaves'])
        assert graph.get('scene')==manifest.get('scene')==SCHEMA
    else:
        assert len(base)==26 and len(set(base.values()))==20
        assert base.get('reset_distribution')=='control_reset_distribution'
    links={k for k,v in instances.items()if v=='control_link8'}
    if links:
        proof=graph['boundary_links'];rows=proof['links']
        assert proof['original_topology_exact_contraction'] and proof['payload_register_bits']==0
        assert links=={r['instance']for r in rows}and proof['new_state_bits']==len(links)
        assert all(r['state_bits']==1 and r['payload_register_bits']==0 for r in rows)
        assert proof['original_instance_count']==(29 if r256 else 26)
        assert len(manifest['leaves'])==(23 if r256 else 21)
        if r256:
            from reset_link_banks import validate as validate_resets
            validate_resets(graph,proof['reset_banks'])
    else:assert len(manifest['leaves'])==(22 if r256 else 20)
    assert set(instances.values())==set(manifest['leaves'])
    assert graph['instance_count']==len(instances)
    internal_s=manifest['leaves']['block_feed_s_macro'].get('S_internal_drive')
    if internal_s:
        assert graph.get('S_internal_drive')==internal_s
        assert graph.get('S_external_link_instances')==0
        assert not any(r['source_instance']=='macro_s'for r in graph.get('boundary_links',{}).get('links',[]))
        assert not any(n.startswith('link_macro_s_')for n in instances)
        assert internal_s['owner']=='block_feed_s_macro M1-M10' and internal_s['all_four_gates_fresh']
        assert internal_s['no_new_registers'] and internal_s['no_latency_or_protocol_change']


def verilog(module):
    def identifier(name):return name if re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*',name)else'\\'+name+' '
    ports=module['ports'];text=['module control_system('+','.join(map(identifier,ports))+');']
    for name,row in ports.items():
        text.append(row['direction']+' '+('['+str(len(row['bits'])-1)+':0] 'if len(row['bits'])>1 else'')+identifier(name)+';')
    bits={b for row in ports.values()for b in row['bits']}|{b for cell in module['cells'].values()for bs in cell['connections'].values()for b in bs}
    assert all(isinstance(bit,int)for bit in bits)
    text+=['wire net_'+str(bit)+';'for bit in sorted(bits)]
    for name,row in ports.items():
        for index,bit in enumerate(row['bits']):
            pin=identifier(name)+('['+str(index)+']'if len(row['bits'])>1 else'');net='net_'+str(bit)
            text.append('assign '+(net+' = '+pin if row['direction']=='input'else pin+' = '+net)+';')
    for name,cell in module['cells'].items():
        assert not cell.get('parameters'),('Unbound physical macro parameters',name)
        terms=[]
        for port,bits in cell['connections'].items():
            terms.append('.'+identifier(port)+'('+('net_'+str(bits[0])if len(bits)==1 else'{'+','.join('net_'+str(bit)for bit in reversed(bits))+'}')+')')
        text.append(identifier(cell['type'])+' '+identifier(name)+'('+','.join(terms)+');')
    text.append('endmodule');return'\n'.join(text)+'\n'
