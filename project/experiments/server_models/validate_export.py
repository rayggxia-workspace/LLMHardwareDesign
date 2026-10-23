"""Independent export/source binding, including full-call versus cached scope."""
import argparse,hashlib,json,math
from pathlib import Path
import numpy as np

def main():
 p=argparse.ArgumentParser();p.add_argument('--capture',required=True,type=Path);p.add_argument('--export',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
 if a.out.exists():raise ValueError('refuse overwrite')
 m=json.loads((a.capture/'manifest.json').read_text());z=np.load(a.capture/'selected-raw.npz',allow_pickle=False);total=0;bytes_checked=0
 for case in m['cases']:
  name=case['name'];folder=a.export/name;doc=json.loads((folder/'capture.json').read_text());expected={}
  def put(name,x):expected[name]=np.ascontiguousarray(x)
  put('token_ids',z[name+'.tokens'].astype('<i8'))
  for layer in m['selected_layers']:
   base=name+'.layer'+str(layer)+'.full.'
   for key in ['q','k','v','reference']:
    x=z[base+key]
    if key in ['k','v']:x=x[None]
    put('layer'+str(layer)+'_'+key,x.astype('<f4'))
  for key in [k for k in z.files if k.startswith('weight.')]:
   label=key[len('weight.'):];stem=label.replace('.','_');base=name+'.linear.'+label+'.';put(stem+'_W',z[key].astype('<f4'));positions=z[base+'rows_within_call']
   for row,pos in enumerate(positions):
    for field in ['A','Y']:put(stem+'_'+field+'_row'+str(int(pos)),z[base+field][row:row+1].astype('<f4'))
   if 'bias.'+label in z.files:put(stem+'_bias',z['bias.'+label].astype('<f4'))
  for key in [k for k in z.files if k.startswith(name+'.norm.')and k.endswith('.input')and'.cached_call'not in k]:
   label=key[len(name+'.norm.'):].removesuffix('.input');base=key[:-5];stem=label.replace('.','_');positions=z[base+'rows_within_call']
   for row,pos in enumerate(positions):
    for field in ['input','output']:put(stem+'_'+field+'_row'+str(int(pos)),z[base+field][row:row+1].astype('<f4'))
   if 'norm_weight.'+label in z.files:put(stem+'_raw_weight',z['norm_weight.'+label].astype('<f4'))
  for key in [k for k in z.files if k.startswith(name+'.hybrid.full.')]:put(key.replace('.','_'),z[key].astype('<f4'))
  if set(expected)!={t['name']for t in doc['tensors']}:raise ValueError('exported field set/phase mismatch')
  for t in doc['tensors']:
   raw=(folder/t['file']['path']).read_bytes();want=expected[t['name']]
   if raw!=want.tobytes(order='C')or list(want.shape)!=t['shape']:raise ValueError('export payload differs from bound native source '+t['name'])
   if 'cached_call'in t['node']:raise ValueError('cached scope in full-call export')
   total+=1;bytes_checked+=len(raw)
 result={'status':'PASS','exported_tensors_bound_to_actual_source':total,'source_bytes_compared':bytes_checked,'scope':'exact actual tensor fields/values/layout; full native-call scope, no cached norm mixing; not model quality','original_capture_manifest_sha256':hashlib.sha256((a.capture/'manifest.json').read_bytes()).hexdigest()}
 a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(result))
if __name__=='__main__':main()
