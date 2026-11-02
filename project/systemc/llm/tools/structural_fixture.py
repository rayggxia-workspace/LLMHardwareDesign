"""Small seeded integration fixture. Never a real-checkpoint/model-quality result."""
import argparse,pathlib,torch,json,subprocess,sys
from transformers import AutoConfig,AutoModelForCausalLM,PreTrainedTokenizerFast
from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from safetensors.torch import save_file

def main():
    ap=argparse.ArgumentParser();ap.add_argument('family');ap.add_argument('directory');a=ap.parse_args()
    torch.set_num_threads(1);torch.manual_seed(153)
    out=pathlib.Path(a.directory);out.mkdir(parents=True,exist_ok=False)
    common=dict(hidden_size=32,intermediate_size=64,num_hidden_layers=2,num_attention_heads=2,
                num_key_value_heads=1,head_dim=16,vocab_size=64,max_position_embeddings=64,
                bos_token_id=1,eos_token_id=2,pad_token_id=0,tie_word_embeddings=True)
    if a.family=='phi3':
        common.update(partial_rotary_factor=.75,original_max_position_embeddings=32,
                      rope_parameters=dict(rope_type='longrope',rope_theta=10000.,partial_rotary_factor=.75,
                                           original_max_position_embeddings=32,short_factor=[1.]*6,long_factor=[2.]*6))
    elif a.family=='gemma3_text':
        common.update(sliding_window=2,query_pre_attn_scalar=16,layer_types=['sliding_attention','full_attention'])
    elif a.family=='qwen3_5_text':
        common.update(layer_types=['linear_attention','full_attention'],linear_num_key_heads=2,
                      linear_num_value_heads=2,linear_key_head_dim=8,linear_value_head_dim=8,linear_conv_kernel_dim=4,
                      rope_parameters=dict(rope_type='default',rope_theta=10000.,partial_rotary_factor=.5,mrope_section=[1,1,2]))
    elif a.family=='falcon_h1':
        common.update(mamba_n_heads=2,mamba_d_head=8,mamba_d_ssm=16,mamba_d_state=8,mamba_n_groups=1,
                      mamba_d_conv=4,mamba_conv_bias=True,mamba_rms_norm=True,mamba_norm_before_gate=False,
                      embedding_multiplier=1.,lm_head_multiplier=1.,ssm_multipliers=[.5]*5,mlp_multipliers=[.5,.5])
    else:raise ValueError(a.family)
    c=AutoConfig.for_model(a.family,**common);c._attn_implementation='eager'
    model=AutoModelForCausalLM.from_config(c).float().eval();c.save_pretrained(out)
    weights={}
    for k,v in model.state_dict().items():
        if a.family=='gemma3_text':name='language_model.'+k
        elif a.family=='qwen3_5_text':name='model.language_model.'+k[len('model.'):] if k.startswith('model.')else k
        else:name=k
        weights[name]=v.contiguous().clone()
    save_file(weights,str(out/'model.safetensors'))
    # Exactly64 token IDs; replace t3 with Hello instead of creating duplicate IDs.
    tokenizer=Tokenizer(WordLevel({('Hello'if i==3 else f't{i}'):i for i in range(64)},unk_token='t0'))
    PreTrainedTokenizerFast(tokenizer_object=tokenizer,unk_token='t0').save_pretrained(out)
    (out/'fixture-scope.json').write_text(json.dumps(dict(scope='seeded small random STRUCTURAL fixture; NOT real checkpoint inference',seed=153,family=a.family))+'\n')
if __name__=='__main__':main()
