"""Config/tokenizer/native backend preflight, no model weights or inference."""
import argparse
import hashlib
import inspect
import json
from pathlib import Path
import time
import traceback


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    if a.out.exists():raise ValueError('refuse overwrite')
    import torch,transformers
    from transformers import AutoConfig,AutoTokenizer
    result={'status':'PASS','torch':torch.__version__,'transformers':transformers.__version__,'models':{}}
    for name,subdir in [('phi','phi4mini-cfbefacb'),('gemma','gemma3-4b-093f9f38')]:
        begin=time.monotonic();r={}
        try:
            directory=a.root/subdir;cfg=AutoConfig.from_pretrained(directory,local_files_only=True,trust_remote_code=False)
            tokenizer=AutoTokenizer.from_pretrained(directory,local_files_only=True,trust_remote_code=False)
            if name=='phi':
                from transformers.models.phi3 import modeling_phi3 as impl
                cls=impl.Phi3ForCausalLM;tc=cfg
            else:
                from transformers.models.gemma3 import modeling_gemma3 as impl
                cls=impl.Gemma3ForConditionalGeneration;tc=cfg.text_config
            path=Path(inspect.getfile(impl))
            r={'status':'PASS','config':cfg.to_dict(),'native_class':cls.__name__,'implementation_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
               'implementation_path':str(path),'tokenizer_class':type(tokenizer).__name__,'tokenizer_probe_ids':tokenizer('A fixed tokenizer preflight.',add_special_tokens=False)['input_ids'],
               'head_dim':getattr(tc,'head_dim',tc.hidden_size//tc.num_attention_heads),'query_heads':tc.num_attention_heads,
               'KV_heads':tc.num_key_value_heads,'layer_types':getattr(tc,'layer_types',None),'forward_signature':str(inspect.signature(cls.forward)),
               'scope':'config/tokenizer/native import only; no inference or integer proof'}
        except Exception as exc:
            result['status']='BLOCKED';r={'status':'BLOCKED','type':type(exc).__name__,'error':str(exc),'traceback':traceback.format_exc()}
        r['seconds']=time.monotonic()-begin;result['models'][name]=r
    a.out.write_text(json.dumps(result,indent=2,default=str)+'\n',newline='\n')
    print(json.dumps({'status':result['status'],'models':{k:v['status']for k,v in result['models'].items()}}))
    if result['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
