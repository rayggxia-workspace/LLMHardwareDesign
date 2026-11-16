"""Standalone, offline input/plan viewer from collected evidence only."""
import argparse
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument('results', type=Path)
    a = p.parse_args()
    def read(name):
        return json.loads((a.results / name).read_text(encoding='utf-8'))
    model = read('imported.json')
    receipt = read('full-model.json')
    data = {'model': {'tasks': model['tasks'], 'sha256': model['sha256']},
            'coverage': read('coverage.json'), 'native': read('native-plan.json'),
            'nativeGraph': read('native-graph.json'), 'nativeHardware': read('native-hardware.json'),
            'receipt': {k: v for k, v in receipt.items() if k not in ('config', 'parameters')}}
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    document = r'''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Block 综合验证记录</title>
<style>
:root{font:15px/1.6 system-ui,sans-serif;color:#172333;background:#f7f8fa}*{box-sizing:border-box}
body{margin:0}main{max-width:1100px;margin:24px auto;padding:0 20px}h1{font-size:25px}h2{font-size:20px;margin-top:30px}
p{max-width:85ch}.muted{color:#536173}svg{width:100%;min-width:760px;height:auto;background:white}svg text{font:12px system-ui;fill:#172333}
#model-graph,#native-graph,#timeline,#memory{overflow-x:auto}
button,select{font:inherit;padding:8px 12px;border:1px solid #9aa7b6;background:white;color:inherit;border-radius:5px}
button[aria-pressed=true]{background:#172333;color:white}button:focus-visible,select:focus-visible{outline:3px solid #5489ba}
.tools{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:16px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}
.stat{padding:12px;background:#fff;border:1px solid #d8dfe7}.stat b{font-size:22px;display:block}.scroll{overflow-x:auto}
table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:8px;border-bottom:1px solid #d8dfe7}code{overflow-wrap:anywhere}button{cursor:pointer}
@media(max-width:500px){main{padding:0 12px;margin-top:12px}h1{font-size:21px}svg text{font-size:13px}}
</style><main>
<h1>Block 综合：输入、生成计划与验证边界</h1>
<p>完整模型前端与原生服务回放分开验收。本页没有把浮点算子当成定点宏服务，也没有用分析代价宣称物理布线通过。</p>
<div class="grid" id="stats"></div>
<div class="tools"><button id="model-tab" aria-pressed="true">完整 Qwen2.5-3B 输入</button><button id="native-tab" aria-pressed="false">生成计划 → 真实 U RTL</button></div>
<section id="model-panel"><h2>模型计算图</h2><p class="muted">概览按真实节点归组；选择一层可展开实际算子和张量依赖。常量和已登记的只读权重布局操作不进入运行时图。</p>
<div class="tools"><label for="layer">查看范围</label><select id="layer"></select><span id="graph-count" aria-live="polite"></span></div><div id="model-graph"></div>
<h2>覆盖检查</h2><p>当前硬件后端只登记了本次实测的 U/E S16 饱和加法服务；其余宏已有实现，尚未被本编译器登记为经过验证的整算子分解规则。因此下面是编译器覆盖缺口，不是硬件不可实现的结论。</p><div class="scroll"><table><thead><tr><th>算子</th><th>格式</th><th>运行时节点</th></tr></thead><tbody id="missing"></tbody></table></div>
<h2>前端数值验证</h2><p id="numeric"></p><p class="muted">B1/S2 prefill、无 KV cache、FP32；三组完整模型输出对照。尚未生成整网宏执行程序。</p></section>
<section id="native-panel" hidden><h2>实际输入依赖图</h2><p>这是原生服务集成测试，使用原验收测试中的整数操作数；不是一个缩小参数量的模型 benchmark。</p><div id="native-graph"></div>
<h2>生成的执行安排</h2><p>输入已在私有 S，四条命令均等待真实 S 写回确认。三种初始化下，结果与 80 周期预测均一致；初始化搬运和 LC 取指不计入这 80 周期。</p><div id="timeline"></div>
<h2>S 地址与存活时间</h2><p id="storage" class="muted"></p><div id="memory"></div><h2>搜索记录</h2><table><thead><tr><th>开放的任务组</th><th>求解状态</th><th>是否采用</th></tr></thead><tbody id="history"></tbody></table>
<p>外存存取、分片、spill/reload、共享副本、静态线束并集和物理端点冲突另有算法测试。它们尚未与母控／局控、五类底座和顶层物理连线一起完成系统验收。</p></section>
</main><script id="data" type="application/json">PAYLOAD</script><script>
const d=JSON.parse(document.getElementById('data').textContent),ns='http://www.w3.org/2000/svg';
const el=id=>document.getElementById(id),esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const colors=['#547fba','#bd7c48','#519287','#956fa2'];
el('stats').innerHTML=[['模型参数', (d.receipt.parameter_count/1e9).toFixed(3)+' B'],['原始 / 简化节点',d.receipt.raw_nodes+' / '+d.receipt.nodes],['原生回放',Object.keys(d.native.tasks).length+' 条 / '+d.native.makespan+' 周期']].map(([k,v])=>'<div class="stat">'+esc(k)+'<b>'+esc(v)+'</b></div>').join('');
function layer(t){const m=t.id.match(/layers[./](\d+)/);return m?'layer '+m[1]:'shared / embedding / head'}
const layers=[...new Set(d.model.tasks.map(layer))].sort((a,b)=>a.startsWith('layer')&&b.startsWith('layer')?Number(a.slice(6))-Number(b.slice(6)):a.startsWith('layer')?1:-1);
el('layer').innerHTML='<option value="overview">整网概览</option>'+layers.map(l=>'<option>'+esc(l)+'</option>').join('');
function graph(host,nodes,edges){
 const ids=new Set(nodes.map(n=>n.id)),ranks=new Map(),pending=[...nodes];
 while(pending.length){let changed=false;for(let i=pending.length-1;i>=0;i--){const n=pending[i],parents=edges.filter(e=>e[1]===n.id&&ids.has(e[0])).map(e=>e[0]);if(parents.every(p=>ranks.has(p))){ranks.set(n.id,parents.length?Math.max(...parents.map(p=>ranks.get(p)))+1:0);pending.splice(i,1);changed=true}}if(!changed){for(const n of pending)ranks.set(n.id,0);break}}
 const groups=new Map();for(const n of nodes){const r=ranks.get(n.id);if(!groups.has(r))groups.set(r,[]);groups.get(r).push(n)}
 const width=1000,rowH=74,pos=new Map();let y=20;
 for(const [rank,group]of [...groups].sort((a,b)=>a[0]-b[0])){for(let i=0;i<group.length;i++){const col=i%5,row=Math.floor(i/5);pos.set(group[i].id,{x:14+col*197,y:y+row*rowH})}y+=Math.ceil(group.length/5)*rowH}
 let out='<svg viewBox="0 0 '+width+' '+(y+10)+'" role="img" aria-label="实际节点依赖图"><defs><marker id="arrow-'+host+'" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0 L7 3.5 L0 7" fill="#9ca9b7"/></marker></defs>';
 for(const[a,b]of edges){if(!pos.has(a)||!pos.has(b))continue;const p=pos.get(a),q=pos.get(b);const bypass=Math.min(990,Math.max(p.x,q.x)+184);const path=q.y-p.y>rowH+2?'M'+(p.x+170)+' '+(p.y+21)+' H'+bypass+' V'+(q.y+21)+' H'+(q.x+170):'M'+(p.x+85)+' '+(p.y+42)+' L'+(q.x+85)+' '+q.y;out+='<path d="'+path+'" stroke="#9caaba" fill="none" marker-end="url(#arrow-'+host+')"><title>'+esc(a+' → '+b)+'</title></path>'}
 for(const n of nodes){const p=pos.get(n.id);out+='<g><rect x="'+p.x+'" y="'+p.y+'" width="170" height="42" rx="3" fill="'+(n.input?'#eef1f4':'#dfeaf6')+'"/><text x="'+(p.x+8)+'" y="'+(p.y+26)+'">'+esc(n.label.slice(0,23))+'</text><title>'+esc(n.title||n.id)+'</title></g>'}
 el(host).innerHTML=out+'</svg>';
}
function renderModel(){const chosen=el('layer').value;if(chosen==='overview'){
 const nodes=layers.map(l=>({id:l,label:l==='shared / embedding / head'?'Embedding / 共享 / Head':l,title:l+' : '+d.model.tasks.filter(t=>layer(t)===l).length+' nodes'}));
 // The overview is a count grid. A selected layer below displays actual
 // tensor edges, without inventing connections from the group order.
 const width=1000,h=Math.ceil(nodes.length/5)*90+20;let html='<svg viewBox="0 0 '+width+' '+h+'" role="img" aria-label="整网分组概览">';
 nodes.forEach((n,i)=>{const x=12+(i%5)*198,y=12+Math.floor(i/5)*90;html+='<rect x="'+x+'" y="'+y+'" width="180" height="64" fill="#dfeaf6"/><text x="'+(x+8)+'" y="'+(y+25)+'">'+esc(n.label)+'</text><text x="'+(x+8)+'" y="'+(y+46)+'">'+d.model.tasks.filter(t=>layer(t)===n.id).length+' 节点</text>'});
 el('model-graph').innerHTML=html+'</svg>';el('graph-count').textContent=d.model.tasks.length+' 个运行时节点；选择范围展开张量边';return;}
 const tasks=d.model.tasks.filter(t=>layer(t)===chosen),producer=new Map(tasks.flatMap(t=>t.outputs.map(o=>[o,t.id]))),edges=[],nodes=tasks.map(t=>({id:t.id,label:t.op,title:t.id+' · '+t.numeric}));
 for(const t of tasks)for(const v of t.inputs){if(producer.has(v))edges.push([producer.get(v),t.id])}
 graph('model-graph',nodes,edges);el('graph-count').textContent=tasks.length+' 个节点 / '+edges.length+' 条范围内依赖';}
el('layer').addEventListener('change',renderModel);renderModel();
el('missing').innerHTML=d.coverage.missing.map(m=>'<tr><td>'+esc(m.op)+'</td><td>'+esc(m.numeric)+'</td><td>'+m.nodes+'</td></tr>').join('');
el('numeric').textContent='三组 HF–ORT 最大绝对误差：'+d.receipt.validation_maxabs.map(x=>x.toExponential(4)).join('、')+'；逐元素 allclose(rtol=3e-4, atol=3e-4) 通过。';
const ng=d.nativeGraph,prod=new Map(ng.tasks.flatMap(t=>t.outputs.map(n=>[n,t.id]))),ni=Object.entries(ng.values).filter(([n,v])=>!v.producer).map(([n])=>({id:'input:'+n,label:n+'（S 输入）',input:true}));
graph('native-graph',[...ni,...ng.tasks.map(t=>({id:t.id,label:t.id+' : '+t.op}))],ng.tasks.flatMap(t=>t.inputs.map(n=>[prod.get(n)||'input:'+n,t.id])));
function timeSvg(rows,kind){const span=d.native.makespan,w=1000,left=130,inner=840,height=45+rows.length*42;let s='<svg viewBox="0 0 '+w+' '+height+'" role="img" aria-label="'+kind+'">';for(let i=0;i<=4;i++){const tick=Math.round(span*i/4),x=left+inner*i/4;s+='<path d="M'+x+' 20 V'+(height-20)+'" stroke="#d6dce5"/><text x="'+x+'" y="15">'+tick+'</text>'}rows.forEach((r,i)=>{const y=30+i*42,x=left+inner*r.start/span,ww=inner*(r.end-r.start)/span;s+='<text x="6" y="'+(y+20)+'">'+esc(r.label)+'</text><rect x="'+x+'" y="'+y+'" width="'+Math.max(1,ww)+'" height="25" fill="'+colors[i%4]+'"/><title>'+esc(r.label)+' ['+r.start+', '+r.end+')</title>'});return s+'</svg>'}
el('timeline').innerHTML=timeSvg(Object.entries(d.native.tasks).sort((a,b)=>a[1].start-b[1].start).map(([id,r])=>({...r,label:id+' / '+r.site})),'执行时间');
const alloc=d.native.allocations.filter(r=>r.value!==null).sort((a,b)=>a.address-b.address||a.start-b.start);
el('memory').innerHTML=timeSvg(alloc.map(r=>({...r,label:r.value+' @ '+r.address})),'S 地址存活区间');
el('storage').textContent='私有 S 共 '+d.nativeHardware.sites['U0.S'].words+' 个 128-bit 字；图中仅显示本测试使用的分配。横轴为周期；区间包含计算和写确认。';
el('history').innerHTML=(d.native.optimization_history||[]).map(r=>'<tr><td>'+esc(r.kind)+'</td><td>'+esc(r.status)+'</td><td>'+(r.accepted?'是':'保留已有计划')+'</td></tr>').join('');
for(const name of ['model','native'])el(name+'-tab').addEventListener('click',()=>{for(const n of ['model','native']){el(n+'-tab').setAttribute('aria-pressed',String(n===name));el(n+'-panel').hidden=n!==name}});
</script></html>'''
    (a.results / 'report.html').write_text(document.replace('PAYLOAD', payload), encoding='utf-8')
    print(json.dumps({'report_bytes': (a.results / 'report.html').stat().st_size}))


if __name__ == '__main__':
    main()
