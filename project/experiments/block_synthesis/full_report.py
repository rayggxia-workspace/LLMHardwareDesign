"""Offline evidence viewer: real input DAG, inventory, loop binding and timing."""
import argparse
import json
from pathlib import Path
import re


def main():
    p=argparse.ArgumentParser();p.add_argument('results',type=Path);a=p.parse_args()
    def load(name):return json.loads((a.results/name).read_text())
    summary=load('summary.json');ir=load('nine-groups-count-experiment-ir.json')
    plan=load('nine-groups-count-experiment-plan.json');base=load('nine-groups-count-experiment-baseline.json')
    original=ir['model']['tasks'];producer={n:i for i,t in enumerate(original) for n in t['outputs']}
    nodes=[]
    for i,t in enumerate(original):
        match=re.search(r'layers\.(\d+)',t['id']);layer=int(match.group(1)) if match else -1
        nodes.append({'id':t['id'],'op':t['op'],'layer':layer,
            'parents':sorted({producer[n] for n in t['inputs'] if n in producer})})
    data={'nodes':nodes,'summary':summary,'plan':plan['tasks'],'baseline':base['tasks'],
        'groups':ir['hardware']['leaf_inventory'],'sites':ir['hardware']['sites'],'program':[
            {k:v for k,v in row.items() if k in ('id','op','shape','exponent','body','temporary_external_region','S_layout')}
            for row in ir['program']],
        'cache_scope':ir.get('read_cache_scope'),
        'sha256':ir['model']['sha256']}
    payload=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    html=r'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>真实 3B 整网：输入与循环调度</title><style>
*{box-sizing:border-box}body{font:15px/1.6 system-ui,sans-serif;margin:0;color:#172333;background:#f6f8fa}
main{max-width:1200px;margin:20px auto;padding:0 18px}h1{font-size:24px}h2{font-size:19px;margin-top:28px}
button,select{font:inherit;padding:6px}table{border-collapse:collapse;width:100%;background:white}td,th{padding:8px;text-align:left;border-bottom:1px solid #ccd4dd}
.scroll{overflow:auto;background:white;margin-top:12px}.notice{padding:14px;background:#fff2d6}svg text{font:12px system-ui;fill:#172333}
#graph,#timeline{max-height:640px}
pre{white-space:pre-wrap;word-break:break-word;background:white;padding:12px;max-height:420px;overflow:auto}
#hardware{display:flex;gap:8px;flex-wrap:wrap}.group{background:white;border:1px solid #ccd4dd;padding:8px 12px}
.tools{display:flex;gap:12px;align-items:center;flex-wrap:wrap}svg{display:block}button{cursor:pointer}
</style><main><h1>Qwen2.5-3B：真实输入 → 循环程序 → 资源调度</h1>
<p>3,085,938,688 参数；完整 embedding、36 层和 LM head；B1/S2 prefill，无 KV cache。</p>
<p class="notice">同一份生成的整数 IR 已完成整网数值回放，并生成有限循环计划。时间是原生命令加虚拟外存的组合模型代价；不是系统周期或物理性能。全部逐步溢出，尚未进行分片缓存复用。程序展示为编译器 IR，尚非局控机器码。</p>
<h2>输入硬件</h2><p>每个控制组使用独立叶宏与 16 KiB 私有 S；数据预连为 0。九组是实例数量实验，不新增物理验收结论。</p><div id="hardware"></div>
<h2>完整图的两组资源对照</h2><div class="scroll"><table><thead><tr><th>资源</th><th>贪心模型代价</th><th>DP 模型代价</th><th>静态逻辑束：贪心 → DP</th><th>搜索合并 / 剪枝</th></tr></thead><tbody id="comparison"></tbody></table></div>
<p id="budget"></p>
<p id="memory"></p><h2>真实算子依赖图</h2><div class="tools"><label>范围 <select id="layer"></select></label><span id="node-count"></span></div><div class="scroll" id="graph"></div>
<h2>对应执行安排</h2><div class="tools"><label>方案 <select id="mode"><option value="plan">DP</option><option value="baseline">贪心</option></select></label><span>按同一层的真实开始/结束时间绘制；单位为组合模型代价。</span></div><div class="scroll" id="timeline"></div>
<h2>节点详情与有限循环</h2><p>点选上图节点，查看来源、精度、循环和临时区域。零搬运视图保留索引变换，不表示免费重排。</p><pre id="detail"></pre>
<h2>整网数值检查</h2><div class="scroll"><table><thead><tr><th>token 输入</th><th>相对 L2</th><th>最大绝对误差</th><th>两位置首选 token</th></tr></thead><tbody id="numeric"></tbody></table></div>
<p>验收门槛在运行前固定：相对 L2 ≤ 2%，三组输入两位置 argmax 均一致。仅覆盖声明的输入与执行范围，不等于困惑度、长上下文或所有模型已验收。</p><p id="hash"></p></main>
<script id="data" type="application/json">PAYLOAD</script><script>
const data=JSON.parse(document.getElementById('data').textContent),$=id=>document.getElementById(id),NS='http://www.w3.org/2000/svg';
const fmt=n=>n.toLocaleString('en-US'),esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function tag(parent,name,attrs,text){const e=document.createElementNS(NS,name);for(const[k,v]of Object.entries(attrs))e.setAttribute(k,v);if(text!==undefined)e.textContent=text;parent.appendChild(e);return e;}
for(const[g,m]of Object.entries(data.groups)){const d=document.createElement('div');d.className='group';d.textContent=g+'  '+m.macros.join(' / ')+' / S '+(data.sites[m.site].words*16/1024)+' KiB';$('hardware').appendChild(d);}
for(const r of data.summary.results){const tr=document.createElement('tr');tr.innerHTML=`<td>${esc(r.scenario)}</td><td>${fmt(r.baseline_bound)}</td><td>${fmt(r.search_bound)}</td><td>${r.baseline_wire_cost} → ${r.search_wire_cost}</td><td>${fmt(r.search_statistics.merged)} / ${fmt(r.search_statistics.pruned)}</td>`;$('comparison').appendChild(tr);}
const r=data.summary.results[1];$('memory').textContent=`外存保留区域（保守、含标量权重和未消除的布局副本）：${(r.required_external_bytes/2**30).toFixed(2)} GiB；硬件未给实际外存容量，容量资格未取得。S 峰值 ${Math.max(...Object.values(r.audit.peak_words))*16} B/站点；全图搬运 ${fmt(r.external_transfer_words)} 个 128-bit 字。`;
const q=r.equal_wire_budget;$('budget').textContent=`九组无束数限制时模型代价降低 ${((1-r.search_bound/r.baseline_bound)*100).toFixed(2)}%，连接束从 ${r.baseline_wire_cost} 增至 ${r.search_wire_cost}。同为 ${q.budget} 束时，搜索代价 ${fmt(q.bound)}，${q.bound===r.baseline_bound?'与贪心相同，没有同连接预算收益。':'详见独立验收。'} 束数是逻辑接口计数，不是实际线长或布通率。`;
for(const c of data.summary.numeric_checks){const tr=document.createElement('tr');tr.innerHTML=`<td>${esc(JSON.stringify(c.ids))}</td><td>${(c.relative_l2*100).toFixed(4)}%</td><td>${c.max_abs.toFixed(5)}</td><td>${c.top1_equal?'一致':'不同'}</td>`;$('numeric').appendChild(tr);}
$('hash').textContent='原始 ONNX SHA-256：'+data.sha256;
for(const layer of [...new Set(data.nodes.map(n=>n.layer))].sort((a,b)=>a-b)){const o=document.createElement('option');o.value=layer;o.textContent=layer<0?'Embedding / 最终归一化 / LM head':'第 '+layer+' 层';$('layer').appendChild(o);}$('layer').value='0';
const programs=new Map(data.program.map(p=>[p.id,p]));
function show(i){$('detail').textContent=JSON.stringify({source:data.nodes[i],program:programs.get(data.nodes[i].id)},null,2);}
function draw(){const layer=Number($('layer').value),indices=data.nodes.map((n,i)=>n.layer===layer?i:-1).filter(i=>i>=0),included=new Set(indices),pos=new Map(),ranks=new Map(),cols=new Map();
for(const i of indices){const rank=Math.max(0,...data.nodes[i].parents.filter(p=>included.has(p)).map(p=>(ranks.get(p)||0)+1));ranks.set(i,rank);const row=cols.get(rank)||0;cols.set(rank,row+1);pos.set(i,[row*145+20,rank*70+25]);}
const width=Math.max(1,...cols.values())*145+20,height=(Math.max(...ranks.values())+1)*70+30;const svg=document.createElementNS(NS,'svg');svg.setAttribute('width',width);svg.setAttribute('height',height);
for(const i of indices){const[x,y]=pos.get(i);for(const p of data.nodes[i].parents){if(!pos.has(p))continue;const[a,b]=pos.get(p);tag(svg,'path',{d:`M${a+59},${b+42} C${a+59},${b+60} ${x+59},${y-20} ${x+59},${y}`,fill:'none',stroke:'#a5b0bd'});}}
for(const i of indices){const[x,y]=pos.get(i),g=tag(svg,'g',{tabindex:0,role:'button','aria-label':data.nodes[i].id});tag(g,'rect',{x,y,width:118,height:42,rx:4,fill:programs.get(data.nodes[i].id)?.body?'#dceafb':'#eef0f3',stroke:'#b7c2ce'});tag(g,'text',{x:x+8,y:y+25},data.nodes[i].op);tag(g,'title',{},data.nodes[i].id);g.addEventListener('click',()=>show(i));g.addEventListener('keydown',e=>{if(e.key==='Enter')show(i);});}
$('graph').replaceChildren(svg);$('node-count').textContent=indices.length+' 个实际节点';show(indices[0]);
const rows=data[$('mode').value].filter(t=>included.has(data.nodes.findIndex(n=>n.id===t.id))).sort((a,b)=>a.start-b.start),s=document.createElementNS(NS,'svg');s.setAttribute('width',1100);s.setAttribute('height',Math.max(70,rows.length*24+40));
const first=Math.min(...rows.map(t=>t.start)),last=Math.max(...rows.map(t=>t.end)),scale=800/Math.max(1,last-first);
rows.forEach((t,j)=>{const y=j*24+20;tag(s,'text',{x:8,y:y+13},t.id.split('/').slice(-2).join('/').slice(0,29));const rect=tag(s,'rect',{x:270+(t.start-first)*scale,y,width:Math.max(1,(t.end-t.start)*scale),height:17,fill:'#4d7faa'});tag(rect,'title',{},`${t.binding}\n${fmt(t.start)} → ${fmt(t.end)}`);});$('timeline').replaceChildren(s);}
$('layer').addEventListener('change',draw);$('mode').addEventListener('change',draw);draw();
</script>'''
    if ir.get('read_cache_scope'):
        html=html.replace('全部逐步溢出，尚未进行分片缓存复用。',
            '已加入 M Dot 输入分量的只读分片缓存，其他结果仍写回外存。跨任务只复用相同 SSA 输入，不缓存脏结果。')
    (a.results/'report.html').write_text(html.replace('PAYLOAD',payload),encoding='utf-8')


if __name__=='__main__':main()
