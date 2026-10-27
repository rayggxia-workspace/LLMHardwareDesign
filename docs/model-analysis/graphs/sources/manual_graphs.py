"""Independently specified tensor-operator graphs; does not read ONNX graphs."""
import argparse,collections,hashlib,json,pathlib,subprocess
from native_export import MODELS,config_for,dump

class Graph:
 def __init__(self,name):self.name=name;self.nodes=[];self.edges=[]
 def op(self,op,*inputs,note=''):
  nid=f'm{len(self.nodes):04d}';self.nodes.append(dict(id=nid,op=op,name=note or op,inputs=list(inputs),outputs=[nid]));self.edges.extend(dict(source=x,target=nid,tensor=x) for x in inputs);return nid
 def finish(self,y):return dict(id=self.name,nodes=self.nodes,edges=self.edges,output=y,op_histogram=dict(collections.Counter(x['op'] for x in self.nodes)),evidence='Manually specified before native ONNX comparison; tensor semantics, not a runtime trace.')

def norm(g,x,tag,zero=False,kind='Mean'):
 s=g.op('Mul',x,x,note=tag+': square');r=g.op('Reduce'+kind,s,note=tag+': reduce last axis');a=g.op('Add',r,note=tag+': + epsilon');q=g.op('Rsqrt',a,note=tag+': inverse sqrt');m=g.op('Mul',x,q,note=tag+': normalize')
 if kind=='Sum':return m
 if zero:
  w=g.op('Add',note=tag+': gamma = 1 + weight');return g.op('Mul',m,w,note=tag+': scale gamma')
 return g.op('Mul',m,note=tag+': scale gamma')

def silu(g,x,tag):return g.op('Mul',x,g.op('Sigmoid',x,note=tag+': sigmoid'),note=tag+': SiLU product')
def rotary(g,x,cos,sin,tag,partial=False):
 if partial:
  base=g.op('Slice',x,note=tag+': rotary channels');pas=g.op('Slice',x,note=tag+': passthrough channels')
 else:base=x
 a=g.op('Slice',base,note=tag+': first half');b=g.op('Slice',base,note=tag+': second half');neg=g.op('Neg',b,note=tag+': negate second half');rot=g.op('Concat',neg,a,note=tag+': rotated vector')
 out=g.op('Add',g.op('Mul',base,cos,note=tag+': cosine product'),g.op('Mul',rot,sin,note=tag+': sine product'),note=tag+': rotate sum')
 return g.op('Concat',out,pas,note=tag+': restore full channels') if partial else out

def attention(g,x,c,name,decode=False):
 cos=g.op('Input',note='cos');sin=g.op('Input',note='sin');mask=g.op('Input',note='causal/window additive mask')
 def proj(w):
  z=g.op('MatMul',x,note=w+' projection')
  if name=='qwen25':z=g.op('Add',z,note=w+' bias')
  return z
 if name=='phi':
  qkv=proj('QKV');q=g.op('Slice',qkv,note='Q channels');k=g.op('Slice',qkv,note='K channels');v=g.op('Slice',qkv,note='V channels')
 elif name=='qwen35_global':
  qg=proj('Q+gate');qh=g.op('Reshape',qg,note='Q+gate per head');q=g.op('Slice',qh,note='Q half');gate=g.op('Slice',qh,note='output-gate half');k=proj('K');v=proj('V')
 else:q=proj('Q');k=proj('K');v=proj('V')
 q=g.op('Reshape',q,note='Q head axes');k=g.op('Reshape',k,note='K head axes');v=g.op('Reshape',v,note='V head axes')
 if name in ['qwen3','qwen35_global','gemma_local','gemma_global']:
  q=norm(g,q,'Q head norm',name.startswith(('gemma','qwen35')));k=norm(g,k,'K head norm',name.startswith(('gemma','qwen35')))
 q=g.op('Transpose',q,note='Q B,H,S,D');k=g.op('Transpose',k,note='K B,H,S,D');v=g.op('Transpose',v,note='V B,H,S,D')
 partial=name in ['phi','qwen35_global','falcon']
 q=rotary(g,q,cos,sin,'Q RoPE',partial);k=rotary(g,k,cos,sin,'K RoPE',partial)
 if decode:
  pk=g.op('StateRead',note='past K');pv=g.op('StateRead',note='past V');k=g.op('Concat',pk,k,note='append K');v=g.op('Concat',pv,v,note='append V')
 if name=='gemma_local' and decode:k=g.op('Slice',k,note='active last 1024 K');v=g.op('Slice',v,note='active last 1024 V')
 g.op('StateWrite',k,note='new K cache');g.op('StateWrite',v,note='new V cache')
 k=g.op('Expand',k,note='GQA shared K');k=g.op('Reshape',k,note='K query-head view');v=g.op('Expand',v,note='GQA shared V');v=g.op('Reshape',v,note='V query-head view')
 kt=g.op('Transpose',k,note='K last two axes');s=g.op('MatMul',q,kt,note='QK scores');s=g.op('Mul',s,note='attention scale');s=g.op('Add',s,mask,note='apply mask');p=g.op('Softmax',s,note='probabilities over keys');o=g.op('MatMul',p,v,note='PV context');o=g.op('Transpose',o,note='context B,S,H,D');o=g.op('Reshape',o,note='merge head axes')
 if name=='qwen35_global':o=g.op('Mul',o,g.op('Sigmoid',gate,note='attention output gate'),note='gate context')
 return g.op('MatMul',o,note='O projection')

def ffn(g,x,name):
 if name=='phi':gu=g.op('MatMul',x,note='fused gate/up projection');gate=g.op('Slice',gu,note='gate half');up=g.op('Slice',gu,note='up half')
 else:gate=g.op('MatMul',x,note='gate projection');up=g.op('MatMul',x,note='up projection')
 if name=='falcon':gate=g.op('Mul',gate,note='FFN gate MuP multiplier')
 if name.startswith('gemma'):
  p=g.op('Pow',gate,note='gate cubed');p=g.op('Mul',p,note='multiply 0.044715');p=g.op('Add',gate,p,note='GELU polynomial');p=g.op('Mul',p,note='multiply sqrt(2/pi)');p=g.op('Tanh',p);p=g.op('Add',p,note='add 1');half=g.op('Mul',gate,note='multiply 0.5');act=g.op('Mul',half,p,note='tanh GELU')
 else:act=silu(g,gate,'FFN gate')
 y=g.op('MatMul',g.op('Mul',act,up,note='gated intermediate'),note='down projection')
 if name=='falcon':y=g.op('Mul',y,note='FFN output MuP multiplier')
 return y

def moe(g,x,c):
 flat=g.op('Reshape',x,note='flatten token axes');r=g.op('MatMul',flat,note='router: 40 logits');ids=g.op('TopK',r,note='top 8 IDs and logits');logits=g.op('Gather',r,ids,note='selected logits');p=g.op('Softmax',logits,note='normalize top8 gates');idx=g.op('Argsort',ids,note='group token/expert assignments');a=g.op('Gather',flat,idx,note='dispatch token rows');w=g.op('Gather',ids,note='selected expert gate/up weights');gu=g.op('MatMul',a,w,note='expert batched gate/up');gate=g.op('Slice',gu,note='gate half');up=g.op('Slice',gu,note='up half');mid=g.op('Mul',silu(g,gate,'expert gate'),up,note='expert gated intermediate');dw=g.op('Gather',ids,note='selected expert down weights');out=g.op('MatMul',mid,dw,note='expert down');out=g.op('Mul',out,p,note='weight expert returns');out=g.op('ScatterAdd',idx,out,note='merge assignments by token');return g.op('Reshape',out,note='restore B,S,H')

def recurrence(g,x,c,name,decode=False):
 gd=name=='qwen35_linear'
 if not gd:x=g.op('Mul',x,note='SSM input MuP multiplier')
 proj=g.op('MatMul',x,note='QKV projection' if gd else 'z/x/B/C/dt fused projection')
 if gd:
  z=g.op('MatMul',x,note='z gate projection');b=g.op('MatMul',x,note='beta projection');beta=g.op('Sigmoid',b);a=g.op('MatMul',x,note='decay time projection')
 else:
  proj=g.op('Mul',proj,note='per-channel MuP multipliers');z=g.op('Slice',proj,note='z gate');a=g.op('Slice',proj,note='raw dt');proj=g.op('Slice',proj,note='x/B/C channels')
 conv=proj
 if decode:conv=g.op('Concat',g.op('StateRead',note='conv history'),conv,note='history plus current token')
 else:conv=g.op('Pad',conv,note='zero-pad causal entry history')
 g.op('StateWrite',g.op('Slice',conv,note='tail of history PLUS current inputs; kernel-width cache'),note='new conv history')
 conv=g.op('Transpose',conv,note='conv channel-first');conv=g.op('Conv',conv,note='depthwise causal Conv1D');conv=g.op('Slice',conv,note='retain causal output positions');conv=silu(g,conv,'conv activation');conv=g.op('Transpose',conv,note='restore sequence-first')
 a=g.op('Add',a,note='dt bias');a=g.op('Softplus',a,note='positive timestep')
 if not gd:a=g.op('Clip',a,note='configured timestep limits')
 al=g.op('Exp',note='exp(A_log)');al=g.op('Neg',al);dec=g.op('Exp',g.op('Mul',al,a,note='negative rate times timestep'),note='state decay')
 q=g.op('Slice',conv,note='Q channels' if gd else 'x channels');k=g.op('Slice',conv,note='K channels' if gd else 'B channels');v=g.op('Slice',conv,note='V channels' if gd else 'C channels')
 if gd:q=norm(g,q,'Q L2',kind='Sum');k=norm(g,k,'K L2',kind='Sum');q=g.op('Mul',q,note='query inverse sqrt(head_dim)');q=g.op('Expand',q,note='repeat Q to value heads');k=g.op('Expand',k,note='repeat K to value heads')
 state=g.op('StateRead' if decode else 'Zeros',note='S at entry')
 for t in range(1 if decode else 2):
  dt=g.op('Gather',dec,note=f't{t}: decay');qt=g.op('Gather',q,note=f't{t}: Q' if gd else f't{t}: x');kt=g.op('Gather',k,note=f't{t}: K' if gd else f't{t}: B');vt=g.op('Gather',v,note=f't{t}: V' if gd else f't{t}: C');sd=g.op('Mul',state,dt,note=f't{t}: decay old state')
  if gd:
   pred=g.op('ReduceSum',g.op('Mul',sd,kt,note=f't{t}: state times K'),note=f't{t}: predict V');delta=g.op('Sub',vt,pred);bt=g.op('Gather',beta,note=f't{t}: beta');delta=g.op('Mul',delta,bt);delta=g.op('Mul',kt,delta,note=f't{t}: K outer delta');state=g.op('Add',sd,delta,note=f't{t}: update state');out=g.op('ReduceSum',g.op('Mul',state,qt),note=f't{t}: Q readout')
  else:
   step=g.op('Gather',a,note=f't{t}: dt');db=g.op('Mul',step,kt,note=f't{t}: dt B');inj=g.op('Mul',db,qt,note=f't{t}: outer x');state=g.op('Add',sd,inj,note=f't{t}: update state');out=g.op('ReduceSum',g.op('Mul',state,vt),note=f't{t}: C readout');out=g.op('Add',out,g.op('Mul',qt,note=f't{t}: D skip'))
  if t==0:outs=[out]
  else:outs.append(out)
 g.op('StateWrite',state,note='final recurrent state');out=g.op('Stack',*outs,note='assemble time outputs');gate=silu(g,z,'output gate')
 if gd:out=norm(g,out,'per-value-head output norm');out=g.op('Mul',out,gate,note='gate normalized readout')
 else:out=g.op('Mul',out,gate,note='gate BEFORE shared norm');out=g.op('Reshape',out,note='merge all 32 heads to 4096');out=norm(g,out,'shared 4096-channel norm')
 return g.op('MatMul',g.op('Reshape',out,note='merge value channels'),note='recurrent output projection')

def make(name,c,decode=False):
 g=Graph(name+('-decode' if decode else '-prefill'));x=g.op('Input',note='hidden input X');zero=name.startswith(('qwen35','gemma'));n=norm(g,x,'input norm',zero)
 if name=='falcon':
  at=attention(g,g.op('Mul',n,note='attention input multiplier'),c,name,decode);at=g.op('Mul',at,note='attention output multiplier');rr=recurrence(g,n,c,name,decode);rr=g.op('Mul',rr,note='SSM output multiplier');mixed=g.op('Add',at,rr,note='sum parallel branches')
 elif name=='qwen35_linear':mixed=recurrence(g,n,c,name,decode)
 else:mixed=attention(g,n,c,name,decode)
 if name.startswith('gemma'):mixed=norm(g,mixed,'post-attention norm',True)
 if name=='granite':mixed=g.op('Mul',mixed,note='residual multiplier 0.22')
 y=g.op('Add',x,mixed,note='attention/mixer residual');n2=norm(g,y,'pre-FFN norm',zero);f=moe(g,n2,c) if name=='granite' else ffn(g,n2,name)
 if name.startswith('gemma'):f=norm(g,f,'post-FFN norm',True)
 if name=='granite':f=g.op('Mul',f,note='residual multiplier 0.22')
 z=g.op('Add',y,f,note='FFN residual');return g.finish(z)

def dot(graph):
 def q(s):return json.dumps(str(s),ensure_ascii=False)
 lines=['digraph G {','graph [rankdir=TB, nodesep=0.22, ranksep=0.38, bgcolor="transparent"];','node [shape=box, style="rounded,filled", fillcolor="#eef3f9", color="#94a3b8", fontname="DejaVu Sans", fontsize=11];','edge [color="#64748b", arrowsize=0.6];']
 for n in graph['nodes']:
  color='#fff1dc' if n['op'] in ['StateRead','StateWrite'] else '#e4f3ec' if n['op'] in ['MatMul','Gemm','Conv'] else '#eef3f9'
  lines.append(f'{q(n["id"])} [label={q(n["id"]+" | "+n["op"]+chr(10)+n.get("name",""))},fillcolor="{color}"];')
 for e in graph['edges']:lines.append(f'{q(e["source"])} -> {q(e["target"])};')
 return '\n'.join(lines+['}'])

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);manifest=[]
 for name in MODELS:
  c=config_for(name)
  for decode in [False,True]:
   g=make(name,c,decode);stem=g['id'];dump(a.out/(stem+'.json'),g);(a.out/(stem+'.dot')).write_text(dot(g),encoding='utf-8');subprocess.run(['dot','-Tsvg',str(a.out/(stem+'.dot')),'-o',str(a.out/(stem+'.svg'))],check=True);manifest.append({'id':stem,'nodes':len(g['nodes']),'edges':len(g['edges']),'sha256':hashlib.sha256((a.out/(stem+'.json')).read_bytes()).hexdigest()})
 dump(a.out/'manifest.json',manifest)

if __name__=='__main__':main()
