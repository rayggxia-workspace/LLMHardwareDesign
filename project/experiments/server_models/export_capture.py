"""Export actual floating captures to the existing strict raw-bin contract.

Retains selected full GQA, individual selected linear/norm rows and true offsets.
No quantization and no holdout tuning; Phi output remains sealed reserved.
"""
import argparse,importlib.util,json,math,sys
from pathlib import Path
import numpy as np
from capture import digest,save
spec=importlib.util.spec_from_file_location('strict_capture',Path(__file__).parent/'integer_precision/capture.py');receiver=importlib.util.module_from_spec(spec);spec.loader.exec_module(receiver)

def main():
 p=argparse.ArgumentParser();p.add_argument('--capture',required=True,type=Path);p.add_argument('--binding',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
 if a.out.exists():raise ValueError('refuse overwrite')
 source=Path(__file__).parent;binding=json.loads(a.binding.read_text())
 for n,expected in binding['sources'].items():
  if digest(source/n)!=expected:raise ValueError('export source SHA '+n)
 manifest=json.loads((a.capture/'manifest.json').read_text())
 if manifest['status']!='PASS':raise ValueError('capture not passed')
 for name,row in manifest['artifacts'].items():
  if digest(a.capture/name)!=row['sha256']:raise ValueError('input SHA')
 z=np.load(a.capture/'selected-raw.npz',allow_pickle=False);a.out.mkdir();index=[]
 weights={n:r for n,r in manifest['files'].items()if n.endswith('.safetensors')};tokens={n:r for n,r in manifest['files'].items()if any(k in n for k in ['token','vocab','merges','chat_template'])}
 save(a.out/'weights-manifest.json',weights);save(a.out/'tokenizer-manifest.json',tokens)
 for case in manifest['cases']:
  name=case['name'];out=a.out/name;out.mkdir();tensors=[];layout={}
  def put(name,value,role,axes,node,layer=-1,selection=None):
   value=np.asarray(value);enc=receiver.encoding('reference_float'if value.dtype.kind=='f'else'unquantized_integer',parameter_generation='not_applicable')
   t=receiver.tensor(out,name,value,role,axes,enc,layer,node)
   if selection is not None:t['selection']=selection
   tensors.append(t)
  ids=z[name+'.tokens'].astype('<i8');put('token_ids',ids,'token_ids',['batch','token'],'model.input')
  for layer in manifest['selected_layers']:
   base=name+'.layer'+str(layer)+'.full.';event=[e for e in case['full_events']if e['layer']==layer][0]
   for key,role in [('q','activation'),('k','kv_key'),('v','kv_value'),('reference','reference_output')]:
    value=z[base+key];is_key=key in ['k','v']
    if is_key:value=value[None]
    shape=event['key_shape'][1:]if is_key else event['query_shape'][1:]
    axes=['kv_head','key_token','channel']if is_key else['q_head','query_token','channel']
    selection={'original_shape':shape,'offsets':[0,0,0],'policy':'all Q heads sharing KV head0, contiguous head selection; full native call after QK norm/RoPE and before optional gate/o_proj'}
    put('layer'+str(layer)+'_'+key,value.astype('<f4'),role,axes,'attention.native_return.'+key,layer,selection)
  for weight in [k for k in z.files if k.startswith('weight.')]:
   label=weight.removeprefix('weight.');layer=int(label.split('.')[0].removeprefix('layer'));base=name+'.linear.'+label+'.'
   xx=z[base+'A'];yy=z[base+'Y'];positions=z[base+'rows_within_call'];ishape=z[base+'input_shape'].tolist();oshape=z[base+'output_shape'].tolist();stem=label.replace('.','_')
   layout[label]={field:z[base+field].tolist()for field in ['input_shape','input_stride','output_shape','output_stride','rows_within_call']}
   put(stem+'_W',z[weight].astype('<f4'),'weight',['output','K'],label+'.weight',layer,{'original_shape':[oshape[-1],ishape[-1]],'offsets':[0,0],'policy':'first16 output channels, complete K'})
   for row,pos in enumerate(positions):
    for suffix,value,role,shape in [('A',xx,'activation',[math.prod(ishape[:-1]),ishape[-1]]),('Y',yy,'reference_output',[math.prod(oshape[:-1]),oshape[-1]])]:
     put(stem+'_'+suffix+'_row'+str(int(pos)),value[row:row+1].astype('<f4'),role,['row','channel'],label+'.'+suffix,layer,{'original_shape':shape,'offsets':[int(pos),0],'policy':'one actual selected row; leading dimensions flattened in row-major order, original shape/stride in layout.json'})
   if 'bias.'+label in z.files:put(stem+'_bias',z['bias.'+label].astype('<f4'),'weight',['output'],label+'.bias',layer,{'original_shape':[oshape[-1]],'offsets':[0],'policy':'first16 output channels'})
  for key in [k for k in z.files if k.startswith(name+'.norm.')and k.endswith('.input')and'.cached_call'not in k]:
   base=key[:-5];label=key[len(name+'.norm.'):].removesuffix('.input');layer=int(label.split('.')[0].removeprefix('layer'));positions=z[base+'rows_within_call'];stem=label.replace('.','_');ishape=z[base+'input_shape'].tolist();oshape=z[base+'output_shape'].tolist()
   layout[label]={field:z[base+field].tolist()for field in ['input_shape','input_stride','output_shape','output_stride','rows_within_call']}
   for row,pos in enumerate(positions):
    for field,role,shape in [('input','activation',ishape),('output','reference_output',oshape)]:
     put(stem+'_'+field+'_row'+str(int(pos)),z[base+field][row:row+1].astype('<f4'),role,['row','channel'],label+'.'+field,layer,{'original_shape':[math.prod(shape[:-1]),shape[-1]],'offsets':[int(pos),0],'policy':'flattened actual norm row; original shape/stride in layout.json'})
   wkey='norm_weight.'+label
   if wkey in z.files:put(stem+'_raw_weight',z[wkey].astype('<f4'),'weight',['channel'],label+'.raw_weight',layer)
  for key in [k for k in z.files if k.startswith(name+'.hybrid.full.')]:
   value=z[key].astype('<f4');role='conv_state'if 'conv_states'in key else'recurrent_state';axes=['batch','channel','history']if value.ndim==3 else['batch','head','key_channel','value_channel']
   put(key.replace('.','_'),value,role,axes,key,0)
  doc={'schema':'llm-precision-capture/1','producer':{'code_commit':binding['commit'],'source_dirty':False,'source_sha256':{'exporter':digest(Path(__file__)),'original_capture_manifest':digest(a.capture/'manifest.json'),'original_source_binding':manifest['source_binding_sha256'],'raw_payload':manifest['artifacts']['selected-raw.npz']['sha256']},'script':str(Path(__file__)),'arguments':sys.argv[1:],'tool_versions':manifest['versions'],'hardware':{'host':manifest['host'],'device':'CPU FP32','capture_threads':str(manifest['threads']),'reserved':str(manifest['sealed_reserved']),'scope_note':'Native full-call GQA before optional gate/o_proj; selected real linear/norm rows; original shape/stride in layout.json; cached observations in original NPZ; no performance measurement'}},'model':{'model_id':manifest['model']['id'],'revision':manifest['model']['revision'],'config_sha256':manifest['files']['config.json']['sha256'],'weights_manifest_sha256':digest(a.out/'weights-manifest.json'),'tokenizer_manifest_sha256':digest(a.out/'tokenizer-manifest.json')},'run':{'phase':'operator','batch':1,'prefix_tokens':0,'new_tokens':int(ids.shape[1]),'input_ids_sha256':tensors[0]['file']['sha256'],'data_version':'fixed native capture token IDs from '+manifest['source_commit'],'calibration_split':'none; sealed reserved model not calibrated'if manifest['sealed_reserved']else'calibration case only; other cases disjoint named validation text','evaluation_split':name,'execution':'floating_reference','backend':'original BF16 checkpoint -> native CPU FP32 capture; raw-bin layout export','floating_fallbacks':['All captured model operators are floating reference; no integer hardware claim'],'measurement_scope':'numerical_only','token_mode':'teacher_forced'},'tensors':tensors}
  save(out/'layout.json',layout);save(out/'capture.json',doc);validated,arrays=receiver.validate(out,binding['commit'],manifest['model']['revision'])
  index.append({'case':name,'validated_tensors':len(arrays),'capture_json_sha256':digest(out/'capture.json'),'layout_sha256':digest(out/'layout.json'),'payload_bytes':sum(t['file']['bytes']for t in tensors)})
 save(a.out/'index.json',{'status':'PASS','source_commit':binding['commit'],'source_capture_manifest_sha256':digest(a.capture/'manifest.json'),'sealed_reserved':manifest['sealed_reserved'],'cases':index,'note':'Strict v1 reference_float data; active integer probe is separately audited, not mislabeled as integer kernel.'})
 print(json.dumps({'status':'PASS','cases':len(index),'tensors':sum(r['validated_tensors']for r in index),'sealed_reserved':manifest['sealed_reserved']}))
if __name__=='__main__':main()
