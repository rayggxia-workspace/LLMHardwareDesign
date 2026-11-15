"""Export full Qwen cached decode with explicit past/present K/V graph edges."""
import os
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
import argparse,json,hashlib
from pathlib import Path
import torch,onnx,onnxsim,numpy as np,onnxruntime as ort
from transformers import AutoModelForCausalLM,DynamicCache

a=argparse.ArgumentParser();a.add_argument('checkpoint');a.add_argument('output',type=Path)
a.add_argument('--past-length',type=int,default=2)
a.add_argument('--frozen-zero-kv',action='store_true')
args=a.parse_args()
if not 1<=args.past_length<=638:raise ValueError('past length outside native ATT1 capacity')
args.output.mkdir(parents=True,exist_ok=False)
torch.set_num_threads(int(os.environ.get('SLURM_CPUS_PER_TASK','4')))
model=AutoModelForCausalLM.from_pretrained(args.checkpoint,local_files_only=True,
                                         torch_dtype=torch.float32,attn_implementation='eager').eval()
class Wrapper(torch.nn.Module):
    def __init__(self,m):super().__init__();self.model=m
    def forward(self,ids,*past):
        cache=DynamicCache(ddp_cache_data=tuple(zip(past[::2],past[1::2])),config=self.model.config)
        mask=torch.zeros((1,1,1,args.past_length+1),dtype=torch.float32)
        result=self.model(input_ids=ids,past_key_values=cache,use_cache=True,
                          position_ids=torch.tensor([[args.past_length]]),
                          attention_mask={'full_attention':mask})
        return (result.logits,*(v for layer in result.past_key_values.layers for v in (layer.keys,layer.values)))
wrapper=Wrapper(model).eval()
with torch.no_grad():
    if args.frozen_zero_kv:
        head_dim=getattr(model.config,'head_dim',model.config.hidden_size//model.config.num_attention_heads)
        past=tuple(torch.zeros((1,model.config.num_key_value_heads,args.past_length,head_dim))
                   for _ in range(2*model.config.num_hidden_layers))
        ids=torch.tensor([[840]])
    else:
        if args.past_length!=2:raise ValueError('real-prefix frontend check currently binds the explicit [1,2] prompt')
        prefill=model(input_ids=torch.tensor([[1,2]]),use_cache=True)
        past=tuple(v.detach().clone() for layer in prefill.past_key_values.layers for v in (layer.keys,layer.values))
        ids=torch.tensor([[3]])
    expected=tuple(v.numpy() for v in wrapper(ids,*past))
    if not args.frozen_zero_kv:
        full=model(input_ids=torch.tensor([[1,2,3]]),use_cache=False).logits[:,-1:,:].numpy()
        np.testing.assert_allclose(expected[0],full,rtol=4e-4,atol=4e-4)
names=['input_ids']+[f'past_{i}_{kind}' for i in range(len(past)//2) for kind in ('key','value')]
outputs=['logits']+[f'present_{i}_{kind}' for i in range(len(past)//2) for kind in ('key','value')]
path=args.output/'decode.onnx'
torch.onnx.export(wrapper,(ids,*past),str(path),input_names=names,output_names=outputs,
                  opset_version=17,dynamo=False,export_params=False,do_constant_folding=False)
graph=onnx.shape_inference.infer_shapes(onnx.load(path));onnx.checker.check_model(graph)
graph,ok=onnxsim.simplify(graph,check_n=0)
if not ok:raise ValueError('decode simplifier rejected graph')
graph=onnx.shape_inference.infer_shapes(graph)
parameters=dict(wrapper.named_parameters());buffers=dict(wrapper.named_buffers())
entry=graph.metadata_props.add();entry.key='block_search.weight_inputs'
entry.value=json.dumps([v.name for v in graph.graph.input if v.name in parameters or v.name in buffers])
onnx.save(graph,path)
options=ort.SessionOptions();options.intra_op_num_threads=torch.get_num_threads();options.inter_op_num_threads=1
session=ort.InferenceSession(str(path),options,providers=['CPUExecutionProvider'])
feed=dict(zip(names,[ids.numpy(),*(v.numpy() for v in past)]))
for v in session.get_inputs():
    if v.name not in feed:
        tensor=parameters.get(v.name,buffers.get(v.name))
        if tensor is None:raise ValueError('unbound decode input '+v.name)
        feed[v.name]=tensor.detach().numpy()
feed={v.name:feed[v.name] for v in session.get_inputs()}
actual=session.run(None,feed)
for x,y in zip(actual,expected):np.testing.assert_allclose(x,y,rtol=4e-4,atol=4e-4)
digest=hashlib.sha256(path.read_bytes()).hexdigest()
bundle={'schema':'algo1-operator-graph-input/1','scope':f'full model cached decode, past length {args.past_length}, query length 1, explicit KV inputs/outputs; no schedule',
        'onnx':{'path':str(path.resolve()),'sha256':digest}}
(args.output/'graph-input.json').write_text(json.dumps(bundle,indent=2)+'\n')
report={'scope':'full cached decode graph; HF vs ORT FP32; uncached-prefix comparison only for non-frozen scene',
        'history_positions':args.past_length,'frozen_zero_kv':args.frozen_zero_kv,
        'nodes':len(graph.graph.node),'past_inputs':len(past),'outputs':len(actual),'onnx_sha256':digest,
        'checkpoint':args.checkpoint,'max_abs_logits':float(np.max(np.abs(actual[0]-expected[0]))),
        'macro_numerically_accepted':False}
(args.output/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
