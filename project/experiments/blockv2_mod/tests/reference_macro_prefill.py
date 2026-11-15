"""Independent full checkpoint prefill reference, never a hardware provider."""
import os,json,time
from pathlib import Path
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
import numpy as np
import torch
from transformers import AutoModelForCausalLM
from macro_assets import filehash
torch.set_num_threads(int(os.environ['SLURM_CPUS_PER_TASK']))
receipt=Path('../full-qwen25-3b-v1/complete/receipt.json')
source=json.loads(receipt.read_text());checkpoint=Path(source['checkpoint'])
out=Path('evidence/architecture-revision-185')/('macro-prefill-reference-'+os.environ['SLURM_JOB_ID'])
out.mkdir(exist_ok=False);start=time.monotonic()
model=AutoModelForCausalLM.from_pretrained(checkpoint,local_files_only=True,torch_dtype=torch.float32,attn_implementation='eager').eval()
tokens=torch.tensor([[1,2]],dtype=torch.long)
with torch.no_grad():result=model(input_ids=tokens,use_cache=True)
logits=result.logits.float().numpy();np.save(out/'logits.npy',logits)
keys={};values={}
for i in range(source['config']['num_hidden_layers']):
 layer=result.past_key_values.layers[i]
 k,v=layer.keys,layer.values
 keys['key_'+str(i)]=k.float().numpy();values['value_'+str(i)]=v.float().numpy()
np.savez(out/'kv.npz',**keys,**values)
metadata={'scope':'independent full checkpoint FP32 reference for short B1 S2 prefill',
 'tokens':tokens.tolist(),'next_token':int(logits[0,-1].argmax()),'logits_shape':list(logits.shape),
 'checkpoint_files_sha256':{p.name:filehash(p) for p in [*sorted(checkpoint.glob('*.safetensors')),checkpoint/'config.json']},
 'source_sha256':filehash(Path(__file__)),'logits_sha256':filehash(out/'logits.npy'),'kv_sha256':filehash(out/'kv.npz'),
 'wall_seconds':time.monotonic()-start,'hardware_acceptance':False}
(out/'receipt.json').write_text(json.dumps(metadata,indent=2)+'\n')
print(json.dumps(metadata),flush=True)
