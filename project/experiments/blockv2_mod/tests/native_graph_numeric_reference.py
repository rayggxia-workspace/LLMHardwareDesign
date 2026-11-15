"""Untimed graph oracle for the declared Q16/W8A16 numeric contract.

Consumes operand-index recipes and sealed initial data, not selected CALLs,
hardware schedules, providers, or their computed results. No performance claim.
"""
import argparse,json,importlib.util,time
from pathlib import Path
from math import isqrt,prod
from collections import OrderedDict
import numpy as np
from native_package_runtime import load
from macro_assets import filehash
from check_softmax import reference as softmax_reference,coefficients
def rne(v,s):
 v=int(v)
 if s<=0:return v<<-s
 q,r=divmod(v,1<<s);return q+int(2*r>1<<s or 2*r==1<<s and q&1)
def checked(v):
 a=np.asarray(v,dtype=np.int64)
 if np.any(a<-(1<<31)) or np.any(a>=1<<31):raise ValueError('numeric contract clips S32')
 return a
def rounded(v,shift):
 v=np.asarray(v,dtype=np.int64);s=np.broadcast_to(np.asarray(shift),v.shape);out=np.empty(v.shape,dtype=np.int64)
 for amount in np.unique(s):
  mask=s==amount;values=v[mask];amount=int(amount)
  if amount<0:
   result=values.astype(object)*(1<<-amount)
   if any(not -(1<<63)<=int(x)<1<<63 for x in result):raise ValueError('reference integer overflow')
   out[mask]=result.astype(np.int64)
  elif amount==0:out[mask]=values
  else:
   q=values>>amount;r=values&((1<<amount)-1);half=1<<(amount-1)
   out[mask]=q+((r>half)|((r==half)&((q&1)!=0)))
 return out
class Oracle:
 def __init__(self,storage,assets,root,g_packet):
  self.storage=storage;self.data={};self.valid={};self.weights={};self.cache=OrderedDict();self.g_packet=g_packet
  self.lut=coefficients()
  for r in assets['regions']:
   p=root/r['file']
   if filehash(p)!=r['sha256']:raise ValueError('reference input seal')
   if r['name'] in storage['weights']:
    n,k=storage['weights'][r['name']]['shape']
    self.weights[r['name']]=np.memmap(p,mode='r',dtype=np.uint8,shape=(n//8,k//128,1088))
   else:self.data[r['name']]=np.memmap(p,mode='r',dtype='<i4',shape=(storage['regions'][r['name']]['bytes']//4,))
 def read(self,a):
  result=np.empty(a['elements'],dtype=np.int64);seen=np.zeros(a['elements'],dtype=bool)
  data=self.data[a['root']];valid=self.valid.get(a['root'])
  for s in a['segments']:
   first=s['source_element'];n=s['elements'];dest=s['destination_element']
   if valid is not None and not valid[first:first+n].all():raise ValueError('oracle unproduced operand')
   result[dest:dest+n]=data[first:first+n];seen[dest:dest+n]=True
  if not seen.all():raise ValueError('oracle incomplete operand')
  return result
 def put(self,w,values):
  values=checked(values)
  if values.size!=w['elements']:raise ValueError('oracle output geometry')
  name=w['value']
  if name not in self.data:
   size=self.storage['regions'][name]['bytes']//4
   self.data[name]=np.empty(size,dtype=np.int64);self.valid[name]=np.zeros(size,dtype=bool)
  start=w['element_offset'];end=start+values.size
  if self.valid[name][start:end].any():raise ValueError('graph output written twice')
  self.data[name][start:end]=values;self.valid[name][start:end]=True
 def matrix(self,x,name):
  key=name,np.asarray(x,dtype='<i4').tobytes()
  if key in self.cache:return self.cache[key]
  n,k=self.storage['weights'][name]['shape'];x=np.asarray(x,dtype=np.int64).reshape(k//128,128)
  shifts=np.array([next(s for s in range(18) if int(np.abs(row).max())<=32767<<s) for row in x])
  activations=rounded(x,shifts[:,None]).reshape(k//128,8,16)
  result=np.empty(n,dtype=np.int64);image=self.weights[name]
  for first in range(0,n//8,32):
   raw=image[first:first+32];groups=len(raw)
   weights=raw[:,:,:1024].reshape(groups,k//128,8,8,16).view(np.int8).astype(np.int64)
   dots=np.einsum('gtkli,tki->gtl',weights,activations,optimize=False)
   bits=np.ascontiguousarray(raw[:,:,1024:1040]).view('<u2').reshape(groups,k//128,8)
   if np.any(bits==0) or np.any(bits>=0x7c00):raise ValueError('invalid positive FP16 scale')
   exponent=bits>>10;mantissa=(bits&1023)+np.where(exponent,1024,0)
   partial=rounded(dots*mantissa,25-np.maximum(exponent.astype(np.int64),1)-shifts[None,:,None])
   checked(partial);prefix=np.cumsum(partial,axis=1,dtype=np.int64);checked(prefix)
   result[first*8:(first+groups)*8]=prefix[:,-1,:].reshape(-1)
  self.cache[key]=result
  while len(self.cache)>4:self.cache.popitem(last=False)
  return result
 def task(self,task):
  kind=task['kind']
  if kind=='View':return
  for row,tile in enumerate(task['tiles']):
   inputs=[self.read(a) for a in tile.get('read',[])];w=tile['write']
   if kind=='Gather':
    index=int(inputs[0][0]);rows=tile['table_rows']
    if index<0:index+=rows
    if not 0<=index<rows:raise ValueError('gather index')
    out=self.data[tile['indexed_table']].reshape(rows,-1)[index]
   elif kind=='MatMul':
    spec=tile['weight'];out=self.matrix(inputs[0],spec['value'])[spec['first_column']:spec['first_column']+spec['columns']]
   elif kind=='Add':out=inputs[0]+inputs[1]
   elif kind=='RMSNorm':
    x,g=inputs;shift=0
    while any(not -32768<=rne(v,shift)<=32767 for v in x):shift+=1
    epsilon=max(1,rne(round(tile['epsilon']*(1<<32)),2*shift))
    square=sum(rne(v,shift)**2 for v in x)
    factor=rne((1<<38)//isqrt((square<<16)//len(x)+(epsilon<<16)),shift)
    normalized=checked([rne(int(v)*factor,14) for v in x])
    out=[rne(int(v)*int(weight),16) for v,weight in zip(normalized,g)]
   elif kind=='RoPE':
    x,c,s=inputs
    rotated=np.concatenate((-x[64:],x[:64]));checked(rotated)
    out=checked(rounded(x*c,14))+checked(rounded(rotated*s,14))
   elif kind=='Attention':
    query=inputs[0];keys=[self.read(a) for a in tile['key_rows']]
    values=[self.read(a) for a in tile['value_rows']];coefficient=round(tile['scale']*(1<<30))
    scores=[rne(int(checked([rne(sum(int(x)*int(y) for x,y in zip(query,key)),16)])[0])*coefficient,30) for key in keys]
    scores=checked(scores).tolist();probabilities=softmax_reference(scores,self.lut)[1]
    out=[rne(sum(int(p)*int(v[i]) for p,v in zip(probabilities,values)),16) for i in range(128)]
   elif kind=='SwiGLUFFN':
    gate,up,down=tile['weights'];a=self.matrix(inputs[0],gate);b=self.matrix(inputs[0],up)
    mid=[]
    for i in range(0,len(a),2):
     pair,error=self.g_packet([int(v) for v in a[i:i+2]],[int(v) for v in b[i:i+2]],True,3)
     if error:raise ValueError('G macro numeric error')
     mid.extend(pair)
    mid=checked(mid)
    for part,vector in (('gate',a),('up',b),('mid',mid)):
     self.put({'value':task['id']+':native:'+part,'element_offset':row*len(vector),'elements':len(vector)},vector)
    out=self.matrix(mid,down)
   elif kind=='Concat':
    # Operand recipes already describe source-indexed output segments.
    out=np.concatenate(inputs)
   else:raise ValueError('unimplemented oracle operator '+kind)
   self.put(w,out)
def main():
 p=argparse.ArgumentParser()
 for name in ('package','assets','recipes','graph','output','g_reference'):p.add_argument(name,type=Path)
 a=p.parse_args();manifest,payloads,_=load(a.package);assets=json.loads(a.assets.read_text())
 graph=json.loads(a.graph.read_text());recipes=json.loads(a.recipes.read_text())
 if not assets['plan_sha256']==manifest['plan_sha256'] or not graph['source_model_sha256']==recipes['source_model_sha256']==manifest['graph_sha256']:
  raise ValueError('oracle input identity')
 a.output.mkdir(exist_ok=False)
 spec=importlib.util.spec_from_file_location('G_numeric_reference',a.g_reference);g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
 storage=json.loads(payloads['storage.json']);oracle=Oracle(storage,assets,a.assets.parent,g.packet);start=time.monotonic()
 for i,task in enumerate(recipes['tasks']):
  oracle.task(task)
  if task['kind']!='View':print(json.dumps({'task':i,'id':task['id'],'kind':task['kind'],'wall_seconds':time.monotonic()-start}),flush=True)
 outputs={}
 for i,name in enumerate(graph['outputs']):
  values=oracle.data[name]
  if name in oracle.valid and not oracle.valid[name].all():raise ValueError('incomplete graph output')
  path=a.output/f'output-{i:03d}.i32le';path.write_bytes(values.astype('<i4').tobytes())
  outputs[name]={'file':path.name,'sha256':filehash(path),'shape':graph['values'][name]['shape'],'exponent':storage['regions'][name]['exponent']}
 committed_values={}
 for i,(name,valid) in enumerate(oracle.valid.items()):
  if not valid.all():raise ValueError('incomplete reference tensor '+name)
  path=a.output/f'value-{i:04d}.i32le';path.write_bytes(oracle.data[name].astype('<i4').tobytes())
  region=storage['regions'][name]
  committed_values[name]={'file':path.name,'sha256':filehash(path),'base':region['base'],'bytes':region['bytes']}
 receipt={'schema':'native-graph-numeric-reference/1','scope':'untimed independent operand-graph fixed-point oracle, not TLM performance',
  'plan_sha256':manifest['plan_sha256'],'graph_sha256':manifest['graph_sha256'],'source_sha256':filehash(Path(__file__)),
  'outputs':outputs,'committed_values':committed_values,'wall_seconds':time.monotonic()-start,'TLM_match_checked':False}
 (a.output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
