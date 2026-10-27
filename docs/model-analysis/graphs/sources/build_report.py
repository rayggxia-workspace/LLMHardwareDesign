"""Build an offline, self-contained review page from frozen graph data and SVGs."""
import collections,csv,hashlib,html,json,pathlib,re,math
ROOT=pathlib.Path(__file__).resolve().parent.parent
LABELS={'qwen25':'Qwen2.5-3B','qwen3':'Qwen3-0.6B','llama':'Llama-3.2-1B','gemma_local':'Gemma-3-4B · 局部层','gemma_global':'Gemma-3-4B · 全局层','phi':'Phi-4-mini','qwen35_global':'Qwen3.5-4B · 全局层','qwen35_linear':'Qwen3.5-4B · 递推层','granite':'Granite-3.3B · MoE','falcon':'Falcon-H1-3B · 混合层'}
NOTES={
 'qwen25':'Q/K/V 三个带偏置的线性投影，简化后由 MatMul + Add 合为 3 个 Gemm。GQA 的 Expand/Reshape 仍存在。',
 'qwen3':'Q、K 各有头内 RMSNorm。head_dim=128，不能用 hidden_size / Q头数推断成64。简化后仍有4组归一化。',
 'llama':'标准 GQA + SwiGLU；没有 Q/K 头内归一化。本机/服务器没有找到原检查点，本轮为报告配置重建 + 固定种子随机参数，不能作为原权重模型验证。',
 'gemma_local':'额外的注意力后、FFN后归一化和 tanh-GELU 都已展开。局部窗口1024；本轮S=2，窗口没有截断任何位置，且掩码、RoPE cos/sin从层外输入，因此图拓扑与全局层相同。不能据此说两者长序列访存相同。',
 'gemma_global':'全局层取第5层，局部层取第0层，两者分别加载实际权重。本次相同节点数来自共同算子结构和S=2的边界，窗口、位置频率与长序列缓存差异未由本轮ONNX验证。',
 'phi':'QKV 合并投影后 Slice，gate/up 也合并投影后拆分；partial RoPE 需要额外的 Slice/Concat。不能把这几个投影当成三条完全独立的数据通路。',
 'qwen35_global':'Q投影同时产出Q和输出门；PV结果之后有 Sigmoid × context，再进入O投影。部分RoPE与Q/K归一化均保留。',
 'qwen35_linear':'原生分块prefill导出因 linalg_solve_triangular 不受支持而失败。成功图仅将递推核替换为Transformers官方逐token等价实现；前向参考仍用原生分块实现。ScatterND对应输出缓冲区写入，不代表跨Block通信。本轮没有导出cached decode。',
 'granite':'40专家、每token top8。手工图画了分组分派/ScatterAdd；导出适配采用动态TopK→Gather专家权重→批量MatMul→ReduceSum。两者是同一数学计算的不同分派实现，不能逐节点硬配。原生路由仍用于三组参考核对。',
 'falcon':'注意力与SSM从同一归一化输入并行分支，再相加。SSM先门乘再做共享4096通道归一化。原生prefill图有Pad、CumSum、Einsum等分块扫描算子，手工图采用两步递推，因而结构显著不同。导出器的负数Transpose轴已按rank取模合法化；原始产物保留。'
}
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def svg(p):
 text=p.read_text(encoding='utf-8');return text[text.index('<svg'):]
items=[];rows=[]
for e in read(ROOT/'results/render01/manifest.json'):
 key=e['model'];version=pathlib.PurePosixPath(e['result']).parent.name;d=ROOT/'results'/version/key
 r=e['receipt'];c=read(d/'config.json');graphs={};views={};paths={}
 for mode in ['manual','decode']:
  stem=key+('-prefill' if mode=='manual' else '-decode');p=ROOT/'results/manual02'/stem
  graphs[mode]=read(p.with_suffix('.json'));views[mode]=svg(p.with_suffix('.svg'));paths[mode]=str(p.with_suffix('.svg').relative_to(ROOT)).replace('\\','/')
 for mode,kind in [('raw','raw'),('sim','simplified')]:
  graphs[mode]=read(d/(kind+'.graph.json'));views[mode]=svg(ROOT/'results/render01'/(key+'-'+kind+'.svg'));paths[mode]='results/render01/'+key+'-'+kind+'.svg'
 err=max(x['raw_native_maxabs'] for x in r['validation']);simerr=max(x['sim_raw_maxabs'] for x in r['validation'])
 stat={'manual':len(graphs['manual']['nodes']),'decode':len(graphs['decode']['nodes']),'raw':r['raw_nodes'],'sim':r['simplified_nodes'],'maxabs':err,'simmaxabs':simerr}
 items.append(dict(key=key,label=LABELS[key],note=NOTES[key],config=c,receipt=r,graphs=graphs,svgs=views,paths=paths,stats=stat,relative=str(d.relative_to(ROOT)).replace('\\','/')))
 rows.append([LABELS[key],stat['manual'],stat['raw'],stat['sim'],err,simerr,r['status']])
with (ROOT/'comparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['模型/层','手工prefill节点(含I/O与状态说明)','原始ONNX节点','简化ONNX节点','三组raw-vs-native最大绝对误差','三组sim-vs-raw最大绝对误差','状态']);w.writerows(rows)
table='\n'.join('| '+' | '.join(str(v) for v in r)+' |' for r in rows)
readme=f'''# 八模型算子计算图与 ONNX/onnxsim 对照

生成日期：2026-10-26；项目：rayggxia-workspace/LLMHardwareDesign。

打开 [交互图册](./operator-graphs.html)。页面内嵌全部SVG与节点数据，离线可用；可切换模型、并列比较、放大图形、点击节点看输入输出和shape。

## 本轮实际交付

- 八个模型，十种decoder层：Qwen2.5、Qwen3、Llama3.2、Gemma3局部/全局、Phi4-mini、Qwen3.5全局/递推、Granite MoE、Falcon-H1。
- 20份独立手工语义算子图（prefill/decode），20份实际ONNX算子图（导出/简化）；SVG、DOT、JSON均保留。
- 十种层均完成定长 B=1、S=2、FP32、eager、eval 的prefill数值核对。原始ONNX对原生前向使用 rtol=atol=3e-4；简化对原始使用 rtol=atol=1e-5；三个随机hidden-state种子17/31/73。它们是层计算核对，不能称为模型任务准确率评测。
- 成功产物索引在 `results/render01/manifest.json`。每个receipt记录工具/源码/权重绑定/文件SHA256。失败尝试保留在native02/03等目录，不把Slurm退出0当成实验成功。

## 范围与证据

这里是完整单decoder层内的算子DAG；不是整个多层网络的一次端到端ONNX导出。词嵌入、RoPE频率生成、掩码生成、最终norm/LM head和采样均不在导出边界；cos/sin与mask是外部输入。层数和混合层序列在各config中可查。

手工decode图显示KV/卷积/递推状态依赖，但本轮没有cached decode ONNX或非零历史状态验证。手工prefill中的StateWrite表示可选缓存接口；实际use_cache=False导出不会保留这些写出。手工图按数学算子语义独立编制，省略常量/权重节点和若干轴广播细节，不是可执行的shape完备IR。

Llama-3.2-1B使用先前报告记录的架构配置重建与随机参数；未找到原检查点。其他模型均加载指定层真实检查点权重，绑定完整性见receipt。

Qwen3.5递推层与Granite各使用一个明确记载的导出适配，数值参考保持原生实现。Falcon仅补入原模型构造时的非持久MuP向量，并将导出器生成的负数Transpose轴按rank取模；未合法化ONNX保存在服务器。

## 实际结果

| 模型/层 | 手工prefill节点 | 原始ONNX节点 | 简化ONNX节点 | raw/native最大绝对误差 | sim/raw最大绝对误差 | 状态 |
|---|---:|---:|---:|---:|---:|---|
{table}

手工数包含Input和状态说明节点；ONNX节点数包含Constant、不含initializer和图I/O。两套口径不同，不应拿手工与ONNX节点数计算优化率。Gemma通过的是绝对+相对容差条件，最大绝对误差可高于3e-4。

## 对比得到的结论

1. onnxsim主要去掉/折叠形状计算、常量和冗余布局节点，也会作局部融合。例如Qwen2.5的三组MatMul+偏置Add变成Gemm。节点更少不等于硬件面积/功耗同比减少。
2. 手工Rsqrt在ONNX中通常是Sqrt+Div；手工平方Mul在ONNX中常是Pow；SiLU仍是Sigmoid+Mul；Gemma的GELU为Tanh等展开。必须先统一算子语义，才能比较覆盖率和Block边界。
3. 同样的模型数学式可有不同算法图：Granite分组scatter与gather-batched-matmul、Falcon分块扫描与逐token递推、Qwen3.5分块与递推核。这是算法/导出边界的差异，不只是简化器删节点。
4. Gemma本次两种层都是110个简化节点，但S=2小于局部窗口，且mask/频率在层外；不能由这个结果得出局部和全局的存储/通信成本相同。
5. 对本项目，这些DAG可以支持算子语义核对、候选Block边界和路由/状态算子的遗漏检查。还不能证明六类或十五类物理Block更好；需要实际精度、长序列prefill/decode、shape/字节数、调度/复用、存储端口、通信切割及面积时序能耗证据。十五项可作为能力标签，六类可作为候选资源族，二者无需一一对应。

## 文件与复现入口

- `results/manual02/`：当前手工图；manual01为首版，manual02修正了卷积history更新必须保留“旧历史+当前输入”的尾部。
- `results/render01/`：原始/简化ONNX完整节点SVG/DOT与成功索引，未隐藏Constant或shape节点。
- `results/native02/`、`native03/`、`native04/`：实际图JSON、配置和receipt；本地包不包含数GB的权重ONNX。
- 服务器完整产物：`yuzelu@10.129.166.172:/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/`。
- 对应的 `raw.onnx` / `simplified.onnx` 在每个成功receipt所在的服务器目录；可按manifest定位，用Netron直接打开。图JSON保留全部算子、数据边、形状和属性，不含权重值。
- `sources/native_export.py`、v2、v3及Slurm脚本为实际执行源码；`sources/manual_graphs.py`不读取ONNX。raw/sim导出源具体版本以receipt的source_sha256为准。
- 依赖：torch2.10.0+cpu、transformers5.20.2、onnx1.17.0、onnxruntime1.20.1、onnxsim v0.8.1。不同工具版本可能产生不同DAG。
- 例：`sbatch sources/batch.sh`；这是已经执行过的固定输出目录脚本，再跑前应另取新输出目录，不能覆盖现有证据。所有重计算应在分配到的Slurm计算节点执行。

## 提交回执

规则版本：rayggxia-project-collab1.0.0；本次是用户授权的旁路实验与本地交付，未改主仓库。
仓库基线：0cc36f3238c7084d7126d94c314fe7d8bf0f9c5d；工作区检查干净。
Issue/PR、登记及看板：本轮未创建/更新；本地包尚未提交项目，不宣称在线任务完成。正式入库动作pending，处理人待指定。
验证：管理检查此前通过；十种层的科学验证逐receipt核实；HTML/SVG核验见本地QA记录。
'''
(ROOT/'README.md').write_text(readme,encoding='utf-8')
page=r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>八模型 · 算子计算图对照</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f5f7fa;color:#182c43;font:14px/1.65 "Microsoft YaHei",system-ui,sans-serif}header{padding:25px 30px 18px;background:#162c44;color:white}h1{font-size:25px;margin:0 0 8px}header p{margin:4px 0;color:#d1dfed}.scope{background:#fff6df;color:#604813;padding:12px 28px;border-bottom:1px solid #eddbb0}.wrap{padding:20px 25px}button,select,input{font:inherit;border:1px solid #bfccda;border-radius:7px;padding:6px 10px;background:white;color:inherit}button{cursor:pointer}button:hover{border-color:#3269a3;background:#edf4fc}button.active{background:#1c527f;color:white;border-color:#1c527f}.models{display:flex;flex-wrap:wrap;gap:7px}.controls{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:15px 0}#search{min-width:240px}.facts{display:flex;gap:10px;flex-wrap:wrap}.facts span{background:white;border:1px solid #d7e0e9;border-radius:8px;padding:7px 13px}.note{background:#eaf1f9;padding:12px 16px;border-left:4px solid #3b6b99;margin:12px 0}.graphs{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:13px}.panel{background:white;border:1px solid #d5dfe9;border-radius:10px;overflow:hidden;min-width:0}.panel header{padding:10px 12px;background:#ecf1f7;color:#243d59;display:flex;flex-wrap:wrap;gap:7px;align-items:center}.panel header strong{margin-right:auto}.tools{display:flex;gap:4px}.tools button{font-size:12px;padding:3px 7px}.viewport{height:720px;overflow:auto;position:relative;overscroll-behavior:contain;background-image:radial-gradient(#ccd6e3 .55px,transparent .55px);background-size:16px 16px}.canvas{display:inline-block;vertical-align:top;min-width:100%;padding:16px}.canvas svg{max-width:none;vertical-align:top}.node{cursor:pointer}.node:hover polygon,.node:hover path{stroke:#004f9a;stroke-width:2.5}.node.match polygon,.node.match path{stroke:#cc4f00;stroke-width:3.4;fill:#fff2cb}.caption{padding:8px 12px;color:#52677d;font-size:12px;border-top:1px solid #e2e8ef}.caption a{color:#1c527f}.inspect{margin:15px 0;display:grid;grid-template-columns:1fr 1fr;gap:14px}.box{background:white;border:1px solid #d5dfe9;border-radius:9px;padding:16px;min-width:0}.box h2{font-size:17px;margin:0 0 10px}pre{white-space:pre-wrap;word-break:break-word;font:12px/1.55 Consolas,monospace;max-height:300px;overflow:auto;margin:0}table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;border-bottom:1px solid #e0e7ef;padding:7px 10px}th{background:#edf2f8}td.num{text-align:right;font-variant-numeric:tabular-nums}.scrolltable{max-height:320px;overflow:auto}details{margin:12px 0}summary{cursor:pointer;font-weight:600}a{color:#1d5d93}footer{padding:20px 25px;background:#eaf0f6;color:#51667c;font-size:12px}.wide{position:fixed;inset:12px;z-index:10;box-shadow:0 0 0 20px #182c43bb}.wide .viewport{height:calc(100vh - 130px)}.overview{margin-top:18px}.pass{color:#207449}#decodewarn{color:#a34b13;font-weight:600}.muted{color:#60758b} @media(max-width:1000px){.graphs{grid-template-columns:1fr}.viewport{height:620px}.inspect{grid-template-columns:1fr}.wrap{padding:15px}} 
</style></head><body><header><h1>八模型 · 算子级计算图对照</h1><p>独立手工语义DAG → PyTorch实际导出ONNX → onnxsim简化ONNX</p><p>8个模型 / 10种decoder层 / 20张手工图 + 20张实际导出图 · 2026-10-26</p></header>
<div class="scope"><b>实际验证范围：</b>完整单decoder层，B=1 / S=2 / FP32 / eager prefill；不是整网端到端导出。mask、cos、sin为层外输入。手工decode有状态接口，未做cached decode ONNX核验。Llama使用重建配置与随机参数；其余用真实层权重。</div>
<div class="wrap"><nav class="models" id="models"></nav><div class="controls"><label>手工图阶段 <select id="phase"><option value="manual">prefill · 两token</option><option value="decode">decode · 单token+历史状态</option></select></label><input id="search" placeholder="查找算子 / 节点名：MatMul、q_norm…"><span id="decodewarn"></span><span class="muted">点击节点查看张量；图可滚动，使用 ± 放大或单图全屏。</span></div>
<div class="facts" id="facts"></div><div id="note" class="note"></div><div class="graphs" id="graphs"></div>
<div class="inspect"><section class="box"><h2>节点详情</h2><pre id="detail">点击任意图中的节点。ONNX节点可查看输入/输出张量名与推断shape；手工图提供语义依赖，未作完备shape标注。</pre></section><section class="box"><h2>当前模型 · 算子直方图</h2><div class="scrolltable"><table><thead><tr><th>算子</th><th>手工</th><th>ONNX</th><th>简化</th></tr></thead><tbody id="hist"></tbody></table></div></section></div>
<section class="box overview"><h2>十种层的实测汇总</h2><p class="muted">手工计数含Input/状态说明，ONNX计数含Constant、不含initializer及图I/O；两者不可直接计算优化率。raw/native采用绝对+相对容差，不能把rtol理解成绝对误差上限。</p><div style="overflow:auto"><table><thead><tr><th>模型 / 层</th><th>手工prefill</th><th>原始ONNX</th><th>onnxsim</th><th>raw/native maxabs</th><th>sim/raw maxabs</th><th>验证</th></tr></thead><tbody id="overview"></tbody></table></div></section>
<section class="box overview"><h2>这些差异如何影响Block研究</h2><p>手工图适合表达数学依赖与状态边界，实际ONNX适合检查实现展开；onnxsim图更便于阅读和算子归并。它们还不是唯一的硬件执行图。先统一语义，再结合shape、精度、时序、复用和存储，确定哪些边跨Block。</p><p>本次能检查常规注意力、Q/K norm、输出门、MoE路由、GDN/SSM状态等能力是否遗漏；不能用节点数直接证明六类或十五类物理Block更好。十五项可作能力标签，六类可作候选资源族。</p><details open><summary>四类已观察到的差异</summary><ul><li>表示方式：Rsqrt → Sqrt + Div；平方Mul → Pow；SiLU → Sigmoid + Mul。</li><li>编译简化：常量、形状计算、冗余布局被折叠；Qwen2.5的MatMul+偏置融合为Gemm。</li><li>算法降低：Granite分组Scatter与动态Gather/MatMul不同；Falcon分块扫描有CumSum/Einsum；Qwen3.5本次导出逐token等价递推核。</li><li>边界遗漏：use_cache=False不会产生历史状态输入输出；S=2不足以暴露局部窗口与长序列带宽，cos/sin与mask在本轮层外。</li></ul></details>
<details><summary>原始产物、源码与证据</summary><p>页面所示JSON、SVG、DOT均在同目录results下；<a href="README.md">详细说明</a> · <a href="comparison.csv">CSV汇总</a> · <a href="results/render01/manifest.json">成功产物与SHA256索引</a>。</p><p>含真实权重的ONNX留在服务器：<code>yuzelu@10.129.166.172:/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/</code>。每个模型所用native02/03/04目录见节点页下的receipt。失败记录和Falcon合法化前产物已保留。没有覆盖其他作业或修改主仓库。</p><p>工具：torch2.10.0+cpu、transformers5.20.2、onnx1.17.0、onnxruntime1.20.1、onnxsim v0.8.1。三组hidden-state种子：17、31、73；raw/native rtol=atol=3e-4，sim/raw rtol=atol=1e-5。本轮不是任务准确率测试，也不是手工图可执行等价性证明。</p></details></section></div>
<footer>手工图独立于ONNX生成；所有显示均为算子节点与依赖边。没有用Attention/MLP等框图替代内部DAG。本地实验交付，未提交GitHub Issue/PR或同步看板。</footer>
<script id="data" type="application/json">__DATA__</script><script>
const DATA=JSON.parse(document.getElementById('data').textContent);let selected=0;const scales={manual:1,raw:1,sim:1};const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const modes=['manual','raw','sim'];const captions={manual:'独立手工语义DAG',raw:'实际导出ONNX · 全部算子',sim:'onnxsim结果 · 全部算子'};
document.getElementById('models').innerHTML=DATA.map((m,i)=>`<button data-i="${i}">${esc(m.label)}</button>`).join('');document.getElementById('models').onclick=e=>{if(e.target.dataset.i!==undefined){selected=Number(e.target.dataset.i);draw()}};
function effective(mode){return mode==='manual'?document.getElementById('phase').value:mode}
function size(mode,factor){scales[mode]=Math.max(.08,Math.min(4,factor));let s=document.querySelector(`#panel-${mode} svg`);if(!s)return;let v=s.viewBox.baseVal;s.style.width=v.width*scales[mode]+'px';s.style.height=v.height*scales[mode]+'px';document.getElementById('zoom-'+mode).textContent=Math.round(scales[mode]*100)+'%'}
function tools(mode){return `<div class="tools"><button data-act="minus">−</button><span id="zoom-${mode}"></span><button data-act="plus">+</button><button data-act="fit">适宽</button><button data-act="wide">单图全屏</button></div>`}
function draw(){let m=DATA[selected],phase=document.getElementById('phase').value,c=m.config;document.querySelectorAll('#models button').forEach((b,i)=>b.classList.toggle('active',i===selected));document.getElementById('decodewarn').textContent=phase==='decode'?'右两图仍是prefill；仅用于看状态依赖差异，不能作decode等价性比较。':'';
document.getElementById('facts').innerHTML=[`H ${c.hidden_size} / FFN ${c.intermediate_size}`,`层数 ${c.num_hidden_layers}`,`Q头 ${c.num_attention_heads} / KV头 ${c.num_key_value_heads}`,`head_dim ${c.head_dim??c.hidden_size/c.num_attention_heads}`,`原始 ${m.stats.raw} → 简化 ${m.stats.sim} 节点`,`三组数值核对 PASS`].map(x=>`<span>${esc(x)}</span>`).join('');document.getElementById('note').textContent=m.note;
document.getElementById('graphs').innerHTML=modes.map(mode=>{let k=effective(mode);return `<section class="panel" id="panel-${mode}"><header><strong>${captions[mode]} · ${m.graphs[k].nodes.length}节点</strong>${tools(mode)}</header><div class="viewport"><div class="canvas">${m.svgs[k]}</div></div><div class="caption"><a href="${m.paths[k]}" target="_blank">完整SVG</a> · <a href="${mode==='manual'?'results/manual02/'+m.key+(phase==='decode'?'-decode':'-prefill')+'.json':m.relative+'/'+(mode==='sim'?'simplified':'raw')+'.graph.json'}" target="_blank">节点JSON</a> · <a href="${m.relative}/receipt.json" target="_blank">实测回执</a></div></section>`}).join('');
for(let mode of modes){let panel=document.getElementById('panel-'+mode);size(mode,scales[mode]);let vp=panel.querySelector('.viewport');requestAnimationFrame(()=>{let root=[...panel.querySelectorAll('.node')].find(n=>n.querySelector('title')?.textContent===(mode==='manual'?'m0000':'input0'));if(root){let b=root.getBoundingClientRect(),v=vp.getBoundingClientRect();vp.scrollLeft=Math.max(0,b.left-v.left+b.width/2-vp.clientWidth/2);vp.scrollTop=Math.max(0,b.top-v.top-30)}});panel.onclick=e=>{let action=e.target.dataset.act;if(action==='plus')size(mode,scales[mode]*1.25);if(action==='minus')size(mode,scales[mode]/1.25);if(action==='fit')size(mode,(vp.clientWidth-40)/panel.querySelector('svg').viewBox.baseVal.width);if(action==='wide'){panel.classList.toggle('wide');e.target.textContent=panel.classList.contains('wide')?'退出全屏':'单图全屏'}let node=e.target.closest('.node');if(node){let id=node.querySelector('title')?.textContent;let g=m.graphs[effective(mode)];let found=g.nodes.find(n=>n.id===id);document.getElementById('detail').textContent=JSON.stringify({view:mode,phase:mode==='manual'?phase:'prefill',...(found??{id,note:'图边界输入/输出节点'})},null,2)}}}
let ops=[...new Set(modes.flatMap(mode=>Object.keys(m.graphs[effective(mode)].op_histogram)))].sort();document.getElementById('hist').innerHTML=ops.map(op=>`<tr><td>${esc(op)}</td>${modes.map(mode=>`<td class="num">${m.graphs[effective(mode)].op_histogram[op]??0}</td>`).join('')}</tr>`).join('');highlight()}
function highlight(){let term=document.getElementById('search').value.toLowerCase().trim(),m=DATA[selected];for(let mode of modes){let g=m.graphs[effective(mode)];let matches=new Set(g.nodes.filter(n=>[n.id,n.name,n.op].join(' ').toLowerCase().includes(term)).map(n=>n.id));document.querySelectorAll(`#panel-${mode} .node`).forEach(el=>el.classList.toggle('match',!!term&&matches.has(el.querySelector('title')?.textContent)))}}
document.getElementById('phase').onchange=draw;document.getElementById('search').oninput=highlight;document.onkeydown=e=>{if(e.key==='Escape')document.querySelectorAll('.wide').forEach(p=>{p.classList.remove('wide');p.querySelector('[data-act="wide"]').textContent='单图全屏'})};
document.getElementById('overview').innerHTML=DATA.map(m=>`<tr><td>${esc(m.label)}</td><td class="num">${m.stats.manual}</td><td class="num">${m.stats.raw}</td><td class="num">${m.stats.sim}</td><td class="num">${m.stats.maxabs.toExponential(3)}</td><td class="num">${m.stats.simmaxabs.toExponential(3)}</td><td class="pass">PASS · 3 seeds</td></tr>`).join('');draw();
</script></body></html>'''
def strict_json(x):
 if isinstance(x,float) and not math.isfinite(x):return str(x)
 if isinstance(x,dict):return {k:strict_json(v) for k,v in x.items()}
 if isinstance(x,list):return [strict_json(v) for v in x]
 return x
data=json.dumps(strict_json(items),ensure_ascii=False,separators=(',',':'),allow_nan=False).replace('</','<\\/')
(ROOT/'operator-graphs.html').write_text(page.replace('__DATA__',data),encoding='utf-8')
manifest={str(p.relative_to(ROOT)).replace('\\','/'):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [ROOT/'README.md',ROOT/'operator-graphs.html',ROOT/'comparison.csv']}
(ROOT/'delivery-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'models':len(items),'nodes':sum(len(g['nodes']) for x in items for g in x['graphs'].values()),'html_bytes':(ROOT/'operator-graphs.html').stat().st_size},ensure_ascii=False))
