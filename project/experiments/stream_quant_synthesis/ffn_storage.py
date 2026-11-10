"""Capacity/traffic exploration, not a cycle-calibrated or routed FFN mapper.

M1--M10 resources remain explicit. SRAM context capacity never implies the
existing M/LC can save/reload a live context. No unbounded intermediate FIFO.
"""
import json
import math


def study(H=2048,F=11008,P=3,S=16384,contexts=8,N=8,Ktile=128,activation_bytes=4,psum_bytes=12):
    columns=[list(range(p*N,H,P*N)) for p in range(P)]
    outputs=[sum(min(N,H-c) for c in group) for group in columns]
    groups=[math.ceil(len(c)/contexts) for c in columns]
    kb=math.ceil(F/Ktile);mid=F*activation_bytes
    workspace=1536;double_B=2*N*Ktile;double_A=2*Ktile*activation_bytes
    material=dict(name='materialize_Mid_in_DRAM',current_context_protocol_sufficient=True,
        full_graph_G_and_DMA_qualified=False,Mid_write_bytes=mid,
        Mid_read_bytes=mid*sum(groups),gate_up_weight_bytes=2*H*F,
        down_weight_bytes=H*F,mid_full_single_S_fits=mid<=S,
        scratch_peak_per_P=workspace+double_B+double_A,
        context_bytes_per_P=contexts*N*psum_bytes,
        note='Private register contexts remain separate active resources; inter-block transport still needs legal endpoints')
    spill=[]
    for n in outputs:
        raw=n*psum_bytes;padded=math.ceil(raw/64)*64
        footprint=padded+workspace+double_B+double_A
        spill.append(dict(outputs=n,psum_S_bytes=padded,S_peak=footprint,capacity_pass=footprint<=S))
    spilled=dict(name='stream_Mid_once_with_SRAM_partials',capacity=spill,
        Mid_intergroup_payload_bytes=P*mid,local_psum_read_bytes=(kb-1)*H*psum_bytes,
        local_psum_write_bytes=(kb-1)*H*psum_bytes,
        gate_up_weight_bytes=2*H*F,down_weight_bytes=H*F,
        current_context_protocol_sufficient=False,
        missing_service='Partial context save/reload or exact wide external accumulation plus generation/ACK sequencing; not provided by a metal connection')
    # Fixed output ownership, reserve one P0 M context for generating gate/up.
    down_contexts=[contexts-1]+[contexts]*(P-1)
    replay_passes=max(math.ceil(len(cols)/c) for cols,c in zip(columns,down_contexts))
    replay=dict(name='regenerate_Mid_for_each_output_group',passes=replay_passes,
        generator_reserved_contexts=[1]+[0]*(P-1),down_contexts=down_contexts,
        gate_up_weight_bytes=2*H*F*replay_passes,down_weight_bytes=H*F,
        additional_gate_up_weight_bytes=2*H*F*(replay_passes-1),Mid_DRAM_bytes=0,
        qualifier='Mathematical replay candidate; generator/down LC interleaving and transport not implemented')
    mid_shard=math.ceil(math.ceil(F/P)*activation_bytes/64)*64
    distributed=dict(name='distributed_Mid_in_private_S',Mid_S_bytes_per_P=mid_shard,
        S_peak_per_P=mid_shard+workspace+double_B+double_A,
        capacity_pass=mid_shard+workspace+double_B+double_A<=S,
        current_context_protocol_sufficient=True,
        qualifier='Alternative, not exhausted optimum: each output group reads all Mid shards over legal inter-P links; scratch reservation fixed here, no proven overlap or routed endpoint qualification')
    assert sum(outputs)==H and material['scratch_peak_per_P']<=S
    return dict(scope='capacity and payload lower bounds; excludes padding/descriptors/endpoint wires and is not token/s',
        H=H,F=F,P=P,S_bytes_per_P=S,activation_bytes=activation_bytes,psum_bytes=psum_bytes,
        outputs_per_P=outputs,Ktile=Ktile,profiles=[material,spilled,replay,distributed])


def all_studies():
    return [study(activation_bytes=a,psum_bytes=p) for a,p in ((4,12),(2,5))]


if __name__=='__main__':print(json.dumps(all_studies(),indent=2))
