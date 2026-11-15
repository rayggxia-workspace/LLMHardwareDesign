"""FP32 full-request reference using the actual native-selected next input token."""
import os,json,time
from pathlib import Path
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
import numpy as np
import torch
from transformers import AutoModelForCausalLM
from macro_assets import filehash
torch.set_num_threads(int(os.environ['SLURM_CPUS_PER_TASK']))
ev=Path('evidence/architecture-revision-185')
assets=json.loads((ev/'macro-decode-assets-115071/assets.json').read_text())
prefill_assets=json.loads((ev/'macro-prefill-assets-114989/assets.json').read_text())
prompt=next(r for r in prefill_assets['regions'] if r['name']=='input_ids')['origin']['tokens']
token=assets['input_token']
source=json.loads(Path('../full-qwen25-3b-v1/complete/receipt.json').read_text());checkpoint=Path(source['checkpoint'])
actual={p.name:filehash(p) for p in [*sorted(checkpoint.glob('*.safetensors')),checkpoint/'config.json']}
if actual!=assets['checkpoint_files_sha256'] or actual!=prefill_assets['checkpoint_files_sha256']:
 raise ValueError('reference checkpoint mismatch')
out=ev/('macro-decode-reference-'+os.environ['SLURM_JOB_ID']);out.mkdir(exist_ok=False);start=time.monotonic()
model=AutoModelForCausalLM.from_pretrained(checkpoint,local_files_only=True,torch_dtype=torch.float32,attn_implementation='eager').eval()
with torch.no_grad():
 prefill=model(input_ids=torch.tensor([prompt],dtype=torch.long),use_cache=True)
 result=model(input_ids=torch.tensor([[token]],dtype=torch.long),past_key_values=prefill.past_key_values,use_cache=True)
logits=result.logits.float().numpy();np.save(out/'logits.npy',logits)
metadata={'scope':'FP32 full two-token prefill plus one decode using the actual native-selected input token',
 'tokens':[[token]],'prefill_tokens':[prompt],'next_token':int(logits[0,-1].argmax()),
 'logits_shape':list(logits.shape),'checkpoint_files_sha256':actual,
 'source_sha256':filehash(Path(__file__)),'logits_sha256':filehash(out/'logits.npy'),
 'wall_seconds':time.monotonic()-start,'hardware_acceptance':False}
(out/'receipt.json').write_text(json.dumps(metadata,indent=2)+'\n');print(json.dumps(metadata),flush=True)
