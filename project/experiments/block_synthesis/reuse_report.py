"""Offline input, output and memory explanation of the selected cache plans."""
import json


def generate(directory):
    def load(name):return json.loads((directory/name).read_text())
    summary=load('summary.json');ir=load('nine-groups-count-experiment-ir.json')
    plan=load('nine-groups-count-experiment-plan.json');tasks={t['id']:t for t in ir['tasks']}
    selected=[]
    for row in plan['tasks']:
        b=next(b for b in tasks[row['id']]['bindings'] if b['id']==row['binding'])
        if 'read_cache' in b:selected.append({'task':row,'cache':b['read_cache'],
            'S_words':ir['hardware']['sites'][b['read_cache']['site']]['words']})
    data={'summary':summary,'selected':selected,'inventory':ir['hardware']['leaf_inventory']}
    payload=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>3B 综合：分片与片上复用</title><style>
body{font:16px/1.7 system-ui;margin:24px auto;padding:0 24px;max-width:1150px;background:#f7f9fc;color:#172333}
table{border-collapse:collapse;width:100%;background:white}td,th{padding:10px;border-bottom:1px solid #ccd4dd;text-align:left}
select{font:inherit;max-width:100%;padding:6px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:white;padding:16px;max-height:320px;overflow:auto}
svg{max-width:100%;height:auto;background:white}svg text{font:15px system-ui;fill:#172333}.note{background:#fff0d2;padding:16px}.row{display:flex;gap:12px;flex-wrap:wrap}.box{background:white;border:1px solid #bbc9d8;padding:12px;flex:1;min-width:200px}
</style><h1>从“每次读外存”到“在 S 留一段反复用”</h1>
<p class="note">完整 Qwen2.5-3B，B1/S2 prefill。比较的是同一份原生整数运算、同一份 #182 虚拟外存模型。时间为模型代价，不是芯片实测周期。没有更改 M 的累加或最终舍入。</p>
<h2>输入如何使用</h2><div class="row"><div class="box">ONNX → 已数值验收的整数图<br>Dot 的行数、列数、K 与数值分量</div><div class="box">硬件清单 → 独立宏 / 私有 S<br>容量、真实原生命令时间、IO 和上下文</div><div class="box">生成候选 → 前沿 DP<br>实例、缓存长度、开始时间、静态连接并集</div></div>
<p><a href="report.html">打开完整输入 DAG 和输出执行时间图</a>。这些图直接读取本次输入和生成计划。</p>
<h2>同一候选池下的对照</h2><table><thead><tr><th>场景</th><th>旧全部写回基线</th><th>有复用：贪心</th><th>有复用：DP</th><th>外存字数</th><th>逻辑束</th></tr></thead><tbody id="rows"></tbody></table><p id="budget"></p>
<p>“旧 → 有复用贪心”体现复用方案的作用；“有复用贪心 → DP”才体现搜索的作用。等束数结果单列。未给出实际布线资格。</p>
<h2>选中一次真实矩阵乘</h2><select id="choose"></select><p id="description"></p>
<svg viewBox="0 0 1000 170" role="img" aria-label="S 地址占用"><g id="layout"></g></svg>
<p>每个分量仍占一个 128 位记录。S[0:8] 保留原来的操作数、结果和 staging；S[8] 为零包；S[9:] 保留各行的 A 前缀。B 的分量只在一个 K 内复用 staging。其余 A 按需从外存读。</p>
<svg viewBox="0 0 1000 170" role="img" aria-label="一次完整 K 累加"><rect x="30" y="30" width="250" height="80" rx="8" fill="#cfe5fc"/><text x="45" y="62">从 S 读 A 的前缀</text><text x="45" y="90">其余部分从外存搬入</text><path d="M280 70H335" stroke="#567" stroke-width="3"/><rect x="335" y="30" width="300" height="80" rx="8" fill="#d5eede"/><text x="350" y="62">同一个 M 完成全部 K 累加</text><text x="350" y="90">只在最后舍入一次</text><path d="M635 70H690" stroke="#567" stroke-width="3"/><rect x="690" y="30" width="280" height="80" rx="8" fill="#e8def7"/><text x="705" y="62">写回、等待 ACK</text><text x="705" y="90">再算下一列，复用 A</text></svg>
<h2>搜索到底记住什么</h2><p>除任务完成、资源可用时间和静态连接外，每个 M.S 记录“谁的哪段 A、几个分量、保留多长”。同一资源空闲时间相同而 S 内容不同的方案，不能合并。同一 SSA 输入和索引范围匹配才允许命中。换成别的输入时覆盖旧缓存。</p>
<h2>本次生成的具体信息</h2><pre id="detail"></pre>
<p>范围：只读 Dot 分量缓存及 B/零包复用；其他中间结果继续写回外存。没有宣称完成一般跨层脏结果缓存、局控整网二进制或物理验收。思路参考 Timeloop 的循环与数据复用表达，时延和容量仍来自本项目输入。</p>
<script id="data" type="application/json">PAYLOAD</script><script>
const d=JSON.parse(document.getElementById('data').textContent),$=x=>document.getElementById(x),fmt=x=>x.toLocaleString('en-US'),NS='http://www.w3.org/2000/svg';
for(const r of d.summary.results){const tr=document.createElement('tr');for(const x of [r.scenario,fmt(r.all_spill_bound),fmt(r.baseline_bound),fmt(r.search_bound),fmt(r.all_spill_words)+' → '+fmt(r.external_transfer_words),r.baseline_wire_cost+' → '+r.search_wire_cost]){const td=document.createElement('td');td.textContent=x;tr.appendChild(td);}$('rows').appendChild(tr);}
const q=d.summary.results[1].equal_wire_budget;$('budget').textContent=`九组最多 ${q.budget} 束：DP 模型代价 ${fmt(q.bound)}；${q.wire_cost} 束。`;
d.selected.forEach((r,i)=>{const o=document.createElement('option');o.value=i;o.textContent=r.task.id;$('choose').appendChild(o);});
function draw(){const r=d.selected[Number($('choose').value)],c=r.cache;$('description').textContent=`${c.site}：每行保留 ${c.stripe}/${c.K} 个位置，${c.rows} 行、每值 ${c.components[0]} 分量。保留 ${fmt(c.cache_words*16)} B；${r.task.cache_hit?'复用先前任务相同输入的 SRAM 内容':'本次从外存填充'}。`;
$('detail').textContent=JSON.stringify(r,null,2);const g=$('layout');g.replaceChildren();const total=r.S_words,segments=[['原槽 / staging',8,'#d2dbe8'],['零包',1,'#f9d98c'],['A 缓存',c.cache_words,'#87b9ef'],['空闲',total-9-c.cache_words,'#e9edf2']];let offset=0;
for(const [label,n,color]of segments){if(n<=0)continue;const rect=document.createElementNS(NS,'rect');rect.setAttribute('x',30+offset/total*940);rect.setAttribute('y',40);rect.setAttribute('width',n/total*940);rect.setAttribute('height',55);rect.setAttribute('fill',color);const title=document.createElementNS(NS,'title');title.textContent=`${label}: S[${offset}:${offset+n}]，${n*16} B`;rect.appendChild(title);g.appendChild(rect);offset+=n;}
const text=document.createElementNS(NS,'text');text.setAttribute('x',30);text.setAttribute('y',135);text.textContent=`总容量 ${fmt(total*16)} B；本任务峰值 ${(9+c.cache_words)*16} B。悬停查看地址范围。`;g.appendChild(text);}
$('choose').addEventListener('change',draw);if(d.selected.length)draw();
</script></html>'''
    (directory/'reuse.html').write_text(html.replace('PAYLOAD',payload),encoding='utf-8')
