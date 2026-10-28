"""Cost the measured matrix/state subset; explicitly reject full-model claims."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def calculate(root):
    base=root/'work/YUZE-LU/121/review-20261028'
    sources=[]
    def load(path):
        raw=path.read_bytes();sources.append(dict(path=path.relative_to(root).as_posix(),sha256=hashlib.sha256(raw).hexdigest()))
        return json.loads(raw)
    spec=load(root/'project/experiments/block_v1/revision300-model-m-shapes.json')
    configs={Path(c['path']).parent.name:c['config']for c in spec['configs']}
    rows={}
    for p in sorted((base/'model-m-0405/tasks').glob('*/revision300-model-m-benchmark.json')):
        d=load(p);assert d['passed']
        for r in d['measurements']['cases']:
            if r['scenario']=='continuous_supply':
                key=(r['logical_k'],r['logical_n'],r['format_a_bits'],r['format_b_bits'])
                assert key not in rows;rows[key]=r
    recurrent=load(base/'recurrent-resource-budget.json')
    rmodels={r['model']:r for r in recurrent['models']}
    sv={}
    svroot=base/'v-workspace-319-0756/block-v1-20261029-319/tasks'
    svreports=sorted(svroot.glob('*/revision300-sv-workspace.json'))
    assert len(svreports)==5
    for p in svreports:
        d=load(p);assert d['passed']
        for name,digest in d['rtl_sha256'].items():
            assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
        for r in d['measurements']['cases']:
            if r['profile']==0:sv[(r['operation'],r['size'])]=r
    conv=load(base/'r-prefetch-0727/block-v1-20261029-309/tasks/revision300-bench-r-extended/revision300-vr-benchmark.json')
    convrow=next(r for r in conv['measurements']['cases']if r['workload']=='conv4'and r['size']==1 and r['profile']==0)
    assert conv['passed'] and convrow['total_cycles']==sum(p['cycles']for p in convrow['phases'].values())
    assert len(rows)==80

    def matrix(k,n,mcount,formats):
        full,tail=divmod(n,8);parts=[]
        for amount,width in [(full,8),(int(tail>0),tail)]:
            if amount:
                row=rows[(k,width)+formats]
                phases=[row[p]for p in ('preload','work','finalization_and_readback')]
                parts.append(dict(tiles=amount,width=width,batches=math.ceil(amount/mcount),
                    tile_cycles=row['total_cycles'],
                    cycles=math.ceil(amount/mcount)*row['total_cycles'],
                    command_bytes=amount*sum(p['command_container_bytes']for p in phases),
                    response_bytes=amount*sum(p['response_container_bytes']for p in phases),
                    operand_valid_bytes=amount*sum(p['operand_effective_bytes']for p in phases)))
        return dict(k=k,n=n,formats=list(formats),macs=k*n,parts=parts,
                    **{name:sum(p[name]for p in parts)for name in ('cycles','command_bytes','response_bytes','operand_valid_bytes')})

    models=[]
    for model in ['qwen3','qwen25','phi','llama','granite','gemma','qwen35','falcon_h1']:
        config_key={'qwen35':'qwen35_global','falcon_h1':'falcon'}.get(model,model)
        if config_key not in configs:
            matches=[k for k in configs if model.replace('_h1','')in k];assert len(matches)==1
            config_key=matches[0]
        c=configs[config_key];h=c['hidden_size'];inter=c['intermediate_size'];layers=c['num_hidden_layers']
        q=c['num_attention_heads'];kv=c['num_key_value_heads'];dim=c.get('head_dim',h//q)
        # Every descriptor is a real matrix boundary. Independent projections are
        # serialized conservatively; no inter-macro overlap or free weight reuse.
        ordinary=[('q',h,q*dim),('k',h,kv*dim),('v',h,kv*dim),('o',q*dim,h)]
        ffn=[('gate',h,inter),('up',h,inter),('down',inter,h)]
        layer_types=[]
        if model=='qwen35':
            assert (c['linear_num_key_heads'],c['linear_num_value_heads'],c['linear_key_head_dim'],c['linear_value_head_dim'],c['linear_conv_kernel_dim'])==(16,32,128,128,4)
            assert c['layer_types'].count('full_attention')==8 and c['layer_types'].count('linear_attention')==24
            ordinary[0]=('q_and_output_gate',h,2*q*dim)
            layer_types=[dict(name='global',count=8,projections=ordinary+ffn,attention=True),
                dict(name='gdn',count=24,projections=[('qkv',h,8192),('z',h,4096),('beta',h,32),('decay',h,32),('out',4096,h)]+ffn,attention=False)]
        elif model=='falcon_h1':
            assert (c['mamba_d_ssm'],c['mamba_n_heads'],c['mamba_d_head'],c['mamba_n_groups'],c['mamba_d_state'],c['mamba_d_conv'])==(4096,32,128,1,256,4)
            layer_types=[dict(name='hybrid',count=layers,projections=ordinary+[('ssm_in',h,8736),('ssm_out',4096,h)]+ffn,attention=True)]
        elif model=='granite':
            assert c['num_local_experts']==40 and c['num_experts_per_tok']==8
            layer_types=[dict(name='moe',count=layers,projections=ordinary+[('router',h,40)]+[(str(e)+'_'+name,k,n)for e in range(8)for name,k,n in ffn],attention=True)]
        elif model=='gemma':
            layer_types=[dict(name='sliding',count=29,projections=ordinary+ffn,attention=True,window=1024),
                         dict(name='full',count=5,projections=ordinary+ffn,attention=True)]
        else:layer_types=[dict(name='dense',count=layers,projections=ordinary+ffn,attention=True)]
        active_weight_parameters=sum(t['count']*sum(k*n for _,k,n in t['projections'])for t in layer_types)+h*c['vocab_size']
        stored_weight_parameters=active_weight_parameters
        if model=='granite':stored_weight_parameters+=(40-8)*layers*sum(k*n for _,k,n in ffn)
        if not c.get('tie_word_embeddings',False):stored_weight_parameters+=h*c['vocab_size']
        candidate=[]
        for context in [576,2048]:
            for mcount in [1,16,32,64,96]:
                details=[]
                for t in layer_types:
                    ops=[dict(name=name,**matrix(k,n,mcount,(16,8)))for name,k,n in t['projections']]
                    length=min(context,t.get('window',context))
                    if t['attention']:
                        # QK and PV are separate S16/S16 matrices. GQA copies
                        # are streamed per query head; not assumed free in M.
                        ops.extend([dict(name='qk_per_head',repeat=q,**matrix(dim,length,mcount,(16,16))),
                                    dict(name='pv_per_head',repeat=q,**matrix(length,dim,mcount,(16,16)))])
                    totals={key:t['count']*sum(o.get('repeat',1)*o[key]for o in ops)for key in ('cycles','macs','command_bytes','response_bytes','operand_valid_bytes')}
                    # Four finite V/S pairs. Full-hidden norms are sequential
                    # layer barriers; independent heads may use four pairs.
                    norm_plan=[(0,h,1)]*(4 if model=='gemma'else 2)
                    if model in ('qwen3','gemma')or(model=='qwen35'and t['attention']):norm_plan.append((0,dim,q+kv))
                    if model=='qwen35'and not t['attention']:norm_plan.extend([(1,128,32),(0,128,32)])
                    if model=='falcon_h1':norm_plan.append((0,4096,1))
                    if t['attention']:norm_plan.append((2,length,q))
                    norm_cycles=sum(math.ceil(repeat/4)*sv[(op,n)]['total_cycles']for op,n,repeat in norm_plan)
                    s_access=sum(repeat*sv[(op,n)]['s_payload_access_bytes']for op,n,repeat in norm_plan)
                    details.append(dict(layer_type=t['name'],layers=t['count'],context=length,operations=ops,totals=totals,
                        norm_softmax_plan=norm_plan,norm_softmax_cycles=t['count']*norm_cycles,
                        s_payload_access_bytes=t['count']*s_access))
                head=matrix(h,c['vocab_size'],mcount,(16,8))
                total={key:sum(t['totals'][key]for t in details)+head[key]for key in ('cycles','macs','command_bytes','response_bytes','operand_valid_bytes')}
                rm=rmodels.get({'falcon_h1':'falcon'}.get(model,model))
                rcycles=next(r['r_stage_cycles']for r in rm['r_count_candidates']if r['count']==6)if rm else 0
                conv_groups=1024 if model=='qwen35'else 576 if model=='falcon_h1'else 0
                conv_layers=24 if model=='qwen35'else 32 if model=='falcon_h1'else 0
                conv_cycles=conv_layers*math.ceil(conv_groups/6)*convrow['total_cycles']
                norm_cycles=sum(t['norm_softmax_cycles']for t in details)+sv[(0,h)]['total_cycles']
                s_access=sum(t['s_payload_access_bytes']for t in details)+sv[(0,h)]['s_payload_access_bytes']
                candidate.append(dict(context=context,m_count=mcount,r_count=6 if rm else 0,
                    v_count=4,s_count=4,norm_softmax_cycles=norm_cycles,s_payload_access_bytes=s_access,
                    convolution_cycles=conv_cycles,convolution_cold_groups_per_token=conv_layers*conv_groups,
                    convolution_container_bytes_each_direction=conv_layers*conv_groups*sum(p['request_container_bytes']for p in convrow['phases'].values()),
                    matrix_stage=total,recurrent_stage_cycles=rcycles,
                    measured_subset_serial_ms=(total['cycles']+rcycles+conv_cycles+norm_cycles)/300000,
                    omitted_stages_have_zero_cost=False,full_model_10tps_qualified=False,
                    layers=details,lm_head=head))
        kv_capacity=sum(t['count']*2*kv*dim*min(2048,t.get('window',2048))*2 for t in layer_types if t['attention'])
        models.append(dict(model=model,config_key=config_key,layers=layer_types,
            s8_active_projection_weight_bytes_per_token=active_weight_parameters,
            s8_matrix_and_embedding_storage_bytes=stored_weight_parameters,
            metadata_norm_bias_not_in_storage_count=True,
            ideal_projection_weight_GBs_at_10tps=active_weight_parameters/1e8,
            s16_kv_capacity_bytes=kv_capacity,candidates=candidate))
    return dict(schema='revision300-resource-budget/1',passed=True,
        clock_hz=300000000,clock_is_planning_assumption=True,
        formats=dict(projection='S16 activation x S8 weight',qk_pv='S16 x S16',state='existing S32 state / S16 factors'),
        tests=[dict(prefill=512,decode_steps=64,capacity=2048,budget_context=576),dict(prefill=1920,decode_steps=128,capacity=2048,budget_context=2048)],
        prefill_latency_measured=False,decode_upper_context_is_conservative=True,
        m_schedule='Each matrix: ceil(full8column tiles/M) measured cold-tile waves, then actual tail tile. Matrix/layer barriers serialized. No free reuse, buffer, broadcast or pipeline overlap.',
        finite_memory='Each M uses its implemented two operand banks and bounded result storage. R uses implemented 8KiB active/8KiB shadow and cold state paths. One V/S pair provides2KiB replay/16KiB workspace, T one6KiB lease. State/KV/weights beyond these capacities require external backing; none assumed resident.',
        unresolved=['The measured global norm/Softmax kernels are charged; learned norm gamma and all uncharged activations/quantization, attention scaling/masking/RoPE and outputs still need explicit schedules.',
            'S32 V/M output to compact S16/S8 input requires explicit finite conversion/packing/address control; current scalar/format primitives do not prove this integrated path.',
            'Conv4 cold coefficient/history load/export and measured norm kernels are charged. Outer gates, S/T handoffs and link RC remain additional to this subset.',
            'Granite dynamic expert ID addressing, loading, weighted reduction; vocabulary host argmax and model tokenizer/quality are not implemented by these macro measurements.',
            'Aggregate command/response container traffic is separate from DRAM bytes. Parallel M waves need independent links and actual memory service; no shared-bus bandwidth is assumed infinite.',
            'Host time is unmeasured.10ms reserve leaves90ms device budget as a planning assumption, not a measured latency.'],
        full_model_10tps_qualified=False,integer_model_quality_qualified=False,
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),sources=sources,models=models)


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('output',type=Path);a=p.parse_args()
    root=Path(__file__).resolve().parents[3];d=calculate(root)
    a.output.write_text(json.dumps(d,indent=2)+'\n')
    for m in d['models']:
        print(m['model'],m['s8_active_projection_weight_bytes_per_token'],[(c['m_count'],round(c['measured_subset_serial_ms'],3))for c in m['candidates']if c['context']==2048])
