"""Derive on-chip demand from frozen repository sample configs; not a runtime simulator."""
import argparse,hashlib,json
from pathlib import Path

FILES=[('qwen25','qwen25.config.json'),('qwen3','qwen3.config.json'),
 ('llama','llama.config.json'),('gemma','gemma_global.config.json'),('phi','phi.config.json'),
 ('qwen35','qwen35_global.config.json'),('granite','granite.config.json'),('falcon','falcon.config.json')]

def derive(directory):
    rows=[]
    for name,file in FILES:
        raw=(directory/file).read_bytes(); c=json.loads(raw.decode('utf-8'))
        h=c['hidden_size'];i=c['intermediate_size'];qh=c['num_attention_heads'];kv=c['num_key_value_heads']
        d=c.get('head_dim',h//qh);t=c['max_position_embeddings'];layers=c['num_hidden_layers']
        experts=c.get('num_local_experts',1); selected=c.get('num_experts_per_tok',1)
        row={'model_key':name,'config_snapshot':file,'config_sha256':hashlib.sha256(raw).hexdigest(),
          'H':h,'I':i,'Q_heads':qh,'KV_heads':kv,'D':d,'layers':layers,'configured_max_positions':t,
          'derived_assumptions':{'batch':1,'activation_bytes_per_element':2,'state_bytes_per_element':4,
             'weight_bytes_s8_scenario':1,'weight_bytes_s16_scenario':2,
             'note':'Planning scenarios, not accepted model quantization; no weights or cache assumed resident.'},
          'one_hidden_S16_bytes':2*h,'one_mid_S16_bytes':2*i,'gate_up_S16_bytes':4*i,
          'one_expert_gated_FFN_weights_S8_bytes':3*h*i,
          'all_expert_gated_FFN_weights_S8_bytes':3*h*i*experts,
          'all_expert_gated_FFN_weights_S16_bytes':6*h*i*experts,
          'experts':experts,'selected_experts':selected,
          'one_attention_layer_KV_S16_at_config_max_bytes':2*t*kv*d*2,
          'all_layers_as_full_attention_KV_S16_upper_bytes':layers*2*t*kv*d*2,
          'KV_upper_kind':'conservative_all_layers_global_no_eviction; overcounts hybrid/local layers',
          'global_softmax_config_max_within_N_count':t<=65535,
          'one_mid_fits_native_S':2*i<=16384,
          'one_mid_fits_conservative_compute_region':2*i<=9216,
          'all_expert_FFN_weights_fit_native_S':3*h*i*experts<=16384,
          'full_inference_admitted_on_current_onchip_contract':False,
          'not_included_in_demands':['other projections/embeddings/norms','alignment/allocator overhead','metadata','all-live tensor peak'],
          'no_external_memory':True}
        if name=='qwen35':
            dims=(c['linear_num_value_heads'],c['linear_key_head_dim'],c['linear_value_head_dim'])
            state=dims[0]*dims[1]*dims[2]*4
            conv_channels=2*c['linear_num_key_heads']*c['linear_key_head_dim']+dims[0]*dims[2]
            row['recurrence']={'kind':'GDN','state_shape':list(dims),'one_layer_state_S32_bytes':state,
               'one_layer_old_plus_next_state_bytes':2*state,
               'conv_channels':conv_channels,'one_layer_conv_history_S32_bytes':3*conv_channels*4,
               'state_fits_native_R_active':state<=8192}
        if name=='falcon':
            dims=(c['mamba_n_heads'],c['mamba_d_head'],c['mamba_d_state'])
            state=dims[0]*dims[1]*dims[2]*4
            conv_channels=c['mamba_d_ssm']+2*c['mamba_n_groups']*c['mamba_d_state']
            row['recurrence']={'kind':'SSM','state_shape':list(dims),'one_layer_state_S32_bytes':state,
               'one_layer_old_plus_next_state_bytes':2*state,
               'conv_channels':conv_channels,'one_layer_conv_history_S32_bytes':3*conv_channels*4,
               'state_fits_native_R_active':state<=8192}
        rows.append(row)
    return {'schema_version':1,'source_ref':'39bd7bf66c47e17c18aa39483c1d974a1e079aa2',
       'scope':'Eight repository samples; arithmetic demand scenarios, no allocation/physical result.',
       'formulas':{'hidden':'B*H*2','mid':'B*I*2','gate_up':'B*I*4',
                   'gated_FFN_weights':'3*H*I*experts*weight_bytes',
                   'KV_one_layer':'2*T*KV_heads*D*2','KV_conservative_all_layers':'layers*KV_one_layer',
                   'state':'product(state_shape)*4','history':'3*conv_channels*4'},
       'models':rows,'external_memory_enabled':False,
       'full_model_memory_completeness':'NOT_CLAIMED: listed demand components, not a full peak-memory plan.'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();result=derive(a.source_dir);a.output.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print(json.dumps({'models':len(result['models']),'external_memory_enabled':False,
                     'full_model_memory_plan':False},ensure_ascii=True))
if __name__=='__main__':main()
