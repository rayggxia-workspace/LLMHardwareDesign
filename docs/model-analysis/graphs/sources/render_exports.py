"""Render every exported ONNX operator node without dropping constants or shape operators."""
import json,pathlib,subprocess
from native_export import MODELS,dump
ROOT=pathlib.Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026')
OUT=ROOT/'results'/'render01';OUT.mkdir(exist_ok=False)
def q(x):return json.dumps(str(x),ensure_ascii=False)
manifest=[]
for model in MODELS:
 selected=None
 for version in ['native04','native03','native02']:
  path=ROOT/'results'/version/model
  if (path/'receipt.json').exists() and json.loads((path/'receipt.json').read_text())['status']=='pass':selected=path;break
 if selected is None:continue
 manifest.append({'model':model,'result':str(selected),'receipt':json.loads((selected/'receipt.json').read_text())})
 for kind in ['raw','simplified']:
  data=json.loads((selected/(kind+'.graph.json')).read_text());lines=['digraph G {','graph [rankdir=TB,nodesep=0.14,ranksep=0.26,bgcolor="transparent"];','node [shape=box,style="rounded,filled",fillcolor="#eef3f9",color="#94a3b8",fontname="DejaVu Sans",fontsize=10];','edge [color="#64748b",arrowsize=0.55];']
  producer={o:n['id'] for n in data['nodes'] for o in n['outputs']}
  for i,x in enumerate(data['inputs']):
   nid='input'+str(i);producer[x['name']]=nid;lines.append(f'{q(nid)} [id={q(nid)},label={q("INPUT: "+x["name"]+chr(10)+str(x["shape"]))},fillcolor="#f0eaff"];')
  for n in data['nodes']:
   shape='; '.join(str(v) for v in n.get('shapes',{}).values());shortname=n['name'].replace('/layer/','/')
   color='#e4f3ec' if n['op'] in ['MatMul','Gemm','Conv'] else '#f3f4f6' if n['op']=='Constant' else '#eef3f9'
   label=n['id']+' | '+n['op']+chr(10)+shortname+chr(10)+shape
   lines.append(f'{q(n["id"])} [id={q(n["id"])},label={q(label)},fillcolor="{color}"];')
   for t in n['inputs']:
    if t in producer:lines.append(f'{q(producer[t])} -> {q(n["id"])};')
  for i,o in enumerate(data['outputs']):
   nid='output'+str(i);lines.append(f'{q(nid)} [label={q("OUTPUT: "+o["name"]+chr(10)+str(o["shape"]))},fillcolor="#f0eaff"];')
   if o['name'] in producer:lines.append(f'{q(producer[o["name"]])} -> {q(nid)};')
  stem=model+'-'+kind;(OUT/(stem+'.dot')).write_text('\n'.join(lines+['}']),encoding='utf-8');subprocess.run(['dot','-Tsvg',str(OUT/(stem+'.dot')),'-o',str(OUT/(stem+'.svg'))],check=True)
dump(OUT/'manifest.json',manifest)
print([(x['model'],x['receipt']['raw_nodes'],x['receipt']['simplified_nodes']) for x in manifest])
