"""Explicit fixed Link8 instances; no active logic in the custom upper layers.

The original native macro pins and RTL stay intact. Every inserted payload
path is recorded and independently contracted back to the exact original
topology. Link8 owns one reset-isolation bit, not a payload pipeline register.
"""
import copy,re


def xy(pin):
    if 'xy_um' in pin:return pin['xy_um']
    box=pin['box_dbu'];return[(box[0]+box[2])/4000,(box[1]+box[3])/4000]


def insert(module,manifest,pins,sources):
    original=copy.deepcopy(module);cells=module['cells']
    assert len(cells)==26 and len(manifest['leaves'])==21
    assert 'control_link8' in manifest['leaves']
    all_bits={bit for cell in cells.values()for bits in cell['connections'].values()for bit in bits}
    all_bits.update(bit for port in module['ports'].values()for bit in port['bits'])
    assert all(isinstance(bit,int)for bit in all_bits)
    next_bit=max(all_bits)+1
    def allocate():
        nonlocal next_bit
        bit=next_bit;next_bit+=1;return bit
    rows=[];replacement={}
    for source in sources:
        assert source in {'macro_s','macro_1','macro_2','macro_3','macro_4','macro_t'}
        cell=cells[source];assert cell['port_directions']['clk']=='input' and cell['port_directions']['reset']=='input'
        clock=cell['connections']['clk'];reset=cell['connections']['reset'];assert len(clock)==len(reset)==1
        w,h=manifest['leaves'][cell['type']]['die_um'];ordered=[]
        sinks={bit for c in original['cells'].values()for port,bits in c['connections'].items()if c['port_directions'][port]=='input'for bit in bits}
        sinks.update(bit for p in original['ports'].values()if p['direction']=='output'for bit in p['bits'])
        for port,bits in cell['connections'].items():
            if cell['port_directions'][port]!='output':continue
            for index,bit in enumerate(bits):
                if bit not in sinks:continue
                pin=port+'['+str(index)+']'if port+'['+str(index)+']'in pins[cell['type']]else port
                x,y=xy(pins[cell['type']][pin]);assert 0<=x<=w and 0<=y<=h
                side=min(range(4),key=lambda s:[x,w-x,y,h-y][s])
                ordered.append((side,y if side<2 else x,pin,bit))
        ordered.sort()
        assert ordered
        for side in range(4):
            group=[row for row in ordered if row[0]==side]
            for offset in range(0,len(group),8):
                chunk=group[offset:offset+8];name='link_'+source+'_'+str(side)+'_'+str(offset//8)
                assert name not in cells
                inputs=[row[3]for row in chunk];inputs+=inputs[:1]*(8-len(inputs))
                outputs=[allocate()for _ in range(8)]
                cells[name]=dict(hide_name=0,type='control_link8',parameters={},attributes={},
                    port_directions=dict(clk='input',reset='input',in_data='input',out_data='output'),
                    connections=dict(clk=clock[:],reset=reset[:],in_data=inputs,out_data=outputs))
                lanes=[]
                for lane,(_,_,pin,old)in enumerate(chunk):
                    assert old not in replacement;replacement[old]=outputs[lane]
                    lanes.append(dict(lane=lane,source_pin=pin,input_bit=old,output_bit=outputs[lane]))
                rows.append(dict(instance=name,source_instance=source,side=side,lanes=lanes,
                    padded_input_lanes=8-len(chunk),clock_bit=clock[0],reset_bit=reset[0],
                    state_owner=name,state_bits=1,payload_register_bits=0))
    for name,cell in original['cells'].items():
        for port,bits in cell['connections'].items():
            if cell['port_directions'][port]=='input':
                cells[name]['connections'][port]=[replacement.get(bit,bit)for bit in bits]
    for port,row in module['ports'].items():
        if row['direction']=='output':row['bits']=[replacement.get(bit,bit)for bit in row['bits']]
    # Independent contraction checks all original connections and ports, not
    # just payload samples. No original active cell or interface disappears.
    contracted=copy.deepcopy(module);reverse={new:old for old,new in replacement.items()}
    for row in rows:del contracted['cells'][row['instance']]
    for cell in contracted['cells'].values():
        for port,bits in cell['connections'].items():cell['connections'][port]=[reverse.get(bit,bit)for bit in bits]
    for port in contracted['ports'].values():port['bits']=[reverse.get(bit,bit)for bit in port['bits']]
    assert contracted==original,'Fixed-link contraction changes original topology'
    return dict(schema='explicit-fixed-native-links/1',original_instance_count=26,links=rows,
        new_state_bits=len(rows),payload_register_bits=0,original_topology_exact_contraction=True,
        reset_contract='Each Link8 samples the same synchronous reset branch as its source macro. Payload is isolated during reset and enabled on the first following clock. No new payload cycle.',
        original_macro_rtl_and_native_geometry_unchanged=True)


def validate(manifest,graph):
    instances=graph['instances'];base={k:v for k,v in instances.items()if v!='control_link8'}
    assert len(base)==26 and len(set(base.values()))==20
    assert base.get('reset_distribution')=='control_reset_distribution'
    links={k for k,v in instances.items()if v=='control_link8'}
    if links:
        proof=graph['boundary_links'];rows=proof['links']
        assert proof['original_topology_exact_contraction'] and proof['payload_register_bits']==0
        assert links=={r['instance']for r in rows}and proof['new_state_bits']==len(links)
        assert all(r['state_bits']==1 and r['payload_register_bits']==0 for r in rows)
        assert len(manifest['leaves'])==21
    else:assert len(manifest['leaves'])==20
    assert set(instances.values())==set(manifest['leaves'])
    assert graph['instance_count']==len(instances)


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
