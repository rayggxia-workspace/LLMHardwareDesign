"""Construct only admitted service bindings on the supplied physical resources."""
from native_tlm_dma import NativeDMA
from native_tlm_u import UArithmetic
from native_tlm_projection import Projection
from native_tlm_attention import Attention
from native_streamed_projection import StreamedProjection
from native_block_services import counted,gather,gated
from native_work_cost import fields
from projection_connections import binding as expected_connection

def build(hardware,wiring,*,clock,dram,memory,srams,g_packet,core_ps):
    overlay=hardware['native_dispatch_overlay']
    if set(srams)!=set(hardware['leaf_inventory']):
        raise ValueError('SRAM instances must match supplied nine-block inventory')
    declared={(t['id'],r['schema'],r['abi'],r['opcode'])
              for t in overlay['targets'] for r in t['routes']}
    targets={t['group']:t['id'] for t in overlay['targets']}
    providers={};models={}
    def add(group,schema,abi,op,provider):
        key=(targets[group],schema,abi,op)
        if key in declared:providers[key]=provider
    def code(s):return int.from_bytes(s.encode(),'little')
    for group,sram in srams.items():
        if group not in targets:continue
        dma=NativeDMA(clock,dram,memory,core_ps=core_ps)
        arithmetic=UArithmetic(clock,sram)
        models[group]={'dma':dma,'arithmetic':arithmetic}
        add(group,3,7,2,arithmetic.add)
        add(group,3,7,3,arithmetic.rms)
        add(group,code('RPE1'),0x02500002,1,arithmetic.rope)
        add(group,code('GSM1'),0x02500002,1,gated(arithmetic,g_packet))
        add(group,code('GTH1'),0x02500002,1,gather(dma,sram))
        for schema,size,store in [('DRL1',512,False),('DRL8',8192,False),
                                  ('DWS1',512,True),('DWS8',8192,True)]:
            add(group,code(schema),0x02500002,1,dma.provider(sram,size=size,store=store))
        add(group,code('DLC1'),0x02500002,1,counted(dma,sram,store=False))
        add(group,code('DSC1'),0x02500002,1,counted(dma,sram,store=True))
        # Attention uses only this physical SRAM aperture, not a hidden source.
        aperture=Projection(clock,dram,memory,sram,sram,source_word=0,scratch_word=512)
        att=Attention(clock,dram,memory,aperture)
        models[group]['attention']=att
        add(group,code('ATT1'),0x02500002,1,att.provider)
    links=[]
    for sink,entry in wiring['bindings'].items():
        if sink.endswith('.lease_valid'):
            dst=sink.split('.')[0]
            src=entry['driver'].split('.')[0]
            link=expected_connection(src,dst,hardware)
            for signal in link['signals']:
                expected={'driver':signal['driver'],'width_bits':signal['width_bits']}
                if wiring['bindings'].get(signal['sink'])!=expected:
                    raise ValueError('incomplete selected projection wiring')
            for tie in link['constant_inputs']:
                if wiring['bindings'].get(tie['sink'])!={'constant':tie['value']}:
                    raise ValueError('incorrect selected projection constant')
            links.append((src,dst))
    if len({s for s,_ in links})!=len(links) or len({d for _,d in links})!=len(links):
        raise ValueError('selected feed link is not a static one-to-one binding')
    f=fields()['input_key']
    for src,dst in links:
        p=Projection(clock,dram,memory,srams[src],srams[dst],source_word=0,scratch_word=512)
        stream=StreamedProjection(p,input_key_offset=f[0],input_key_bytes=f[1])
        models[dst]['projection']=p;models[src]['stream']=stream
        add(dst,0x02505001,0x02504d02,2,stream.projection)
        for op in (1,2):add(src,code('PFED'),0x02500002,op,stream.supplier)
    return providers,models
