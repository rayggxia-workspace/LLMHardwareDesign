from pathlib import Path
from collections import Counter
import csv,gzip,html,json,re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

P=Path(__file__).resolve().parent
SRC=P.parents[1]/'llaccel-engine-analysis-20261020'
D=json.loads((P/'summary.json').read_text(encoding='utf8'));R=D['results'];KEYS=list(D['labels'])
SHORT=['GEMM 权重读取','GEMM A／参数读取','VECTOR 读口 0','VECTOR 读口 1','GEMM 结果写回','VECTOR 结果写回']
plt.rcParams.update({'font.family':'Microsoft YaHei','axes.unicode_minus':False,'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.facecolor':'white'})
LAYERS=['metal'+str(i) for i in range(2,11)]
COLORS=['#2563a6','#36a3bc','#48a47b','#e5a124','#d65a48','#9872b6','#845940','#d369a3','#656b75']

def save(fig,name):
 fig.savefig(P/(name+'.png'),dpi=190,bbox_inches='tight');fig.savefig(P/(name+'.svg'),bbox_inches='tight');plt.close(fig)

fig,axs=plt.subplots(1,2,figsize=(14,5.5),gridspec_kw={'width_ratios':[1,1.1]})
for ax,pct in zip(axs,[False,True]):
 left=np.zeros(len(KEYS))
 for l,c in zip(LAYERS,COLORS):
  vals=np.array([R[k]['layers_um'].get(l,0)/(R[k]['length_um']/100 if pct else 1000) for k in KEYS])
  ax.barh(np.arange(len(KEYS)),vals,left=left,color=c,label=l.replace('metal','M'),height=.65);left+=vals
 ax.set_yticks(range(len(KEYS)),SHORT if not pct else ['']*len(KEYS));ax.invert_yaxis()
 ax.set_xlabel('各物理网线长之和（mm）' if not pct else '按线长计的金属层占比（%）')
 ax.set_title('所追踪的整个读写通路' if not pct else '同一通路的逐层比例',loc='left',fontweight='bold')
 ax.grid(axis='x',alpha=.17);ax.set_axisbelow(True)
 if pct:ax.set_xlim(0,100)
 else:
  for i,k in enumerate(KEYS):ax.text(left[i]+25,i,f'{left[i]:,.1f}',va='center',fontsize=9)
  ax.set_xlim(0,max(left)*1.15)
fig.legend(*axs[0].get_legend_handles_labels(),loc='lower center',ncol=9,bbox_to_anchor=(.55,-.035),frameon=False)
fig.suptitle('llaccel：SRAM bank 边界与数据状态之间的布线',x=.09,ha='left',fontweight='bold',fontsize=16)
fig.text(.09,-.075,'每条通路内部整网去重；不同通路存在共享，不能把六项线长相加。GEMM A／参数路径包含进入首级乘法寄存器前的组合计算。',fontsize=9,color='#546176')
fig.tight_layout(rect=[0,.04,1,.94]);save(fig,'01-path-layers')

fig,ax=plt.subplots(figsize=(12,5.8));yy=np.arange(6);w=.24
for off,suffix,label,c in [(-w,'_STATE_DIRECT','直接接在数据寄存器 D／Q 上的网','#94a9bb'),(0,'_STATE_LEG','再延伸经过 BUF／INV 的连线','#428aa2'),(w,'','所追踪的整个通路','#c27442')]:
 v=[R[k+suffix]['M4plus_pct'] for k in KEYS];ax.barh(yy+off,v,height=w*.88,label=label,color=c)
 for i,x in enumerate(v):ax.text(x+1,yy[i]+off,f'{x:.1f}%',va='center',fontsize=8)
ax.set_yticks(yy,SHORT);ax.invert_yaxis();ax.set_xlim(0,105);ax.set_xlabel('M4 及以上占比（按线长）');ax.grid(axis='x',alpha=.16);ax.set_axisbelow(True)
ax.set_title('“寄存器端”不等于“低层短线”：VECTOR 写回是明显例子',loc='left',fontweight='bold',pad=16)
fig.legend(*ax.get_legend_handles_labels(),loc='lower center',bbox_to_anchor=(.60,.015),ncol=1,frameon=False)
fig.tight_layout(rect=[0,.19,1,1]);save(fig,'02-scope-comparison')

bk=['bank_rdata','bank_wdata','bank_addr','bank_we','bank_en'];bn=['SRAM bank 读数据输入 · 2048 bit','SRAM bank 写数据输出 · 2048 bit','SRAM bank 地址输出 · 256 bit','SRAM bank 字节写掩码 · 256 bit','SRAM bank 使能输出 · 16 bit']
fig,ax=plt.subplots(figsize=(12,4.4));left=np.zeros(len(bk))
for l,c in zip(LAYERS,COLORS):
 v=[100*R[k]['layers_um'].get(l,0)/R[k]['length_um'] for k in bk];ax.barh(range(len(bk)),v,left=left,color=c,label=l.replace('metal','M'));left+=v
ax.set_yticks(range(len(bk)),bn);ax.invert_yaxis();ax.set_xlim(0,100);ax.set_xlabel('对应顶层引脚所接物理网的逐层线长占比（%）')
ax.set_title('按对外功能区分：SRAM bank 边界的直接连线',loc='left',fontweight='bold',pad=15)
ax.legend(ncol=9,bbox_to_anchor=(.5,-.25),loc='lower center',frameon=False);fig.tight_layout();save(fig,'03-bank-functions')

with gzip.open(P/'path_cells.json.gz','rt',encoding='utf8') as f:pc=json.load(f)
base=[];states={};ev=json.loads((P/'endpoint_evidence.json').read_text(encoding='utf8'))
needed={n for k in ['GEMM_WEIGHT','VECTOR_WRITE'] for n,p,i in ev[k]['state_pins']}
with gzip.open(SRC/'compact_physical_evidence.jsonl.gz','rt',encoding='utf8') as f:
 for line in f:
  a=json.loads(line)
  if not isinstance(a,list):continue
  if a[0]!='c':break
  x1,y1,x2,y2=a[4];pt=((x1+x2)/4000,(y1+y2)/4000);base.append(pt)
  if a[2].replace('\\','') in needed:states[a[2].replace('\\','')]=pt
base=np.array(base);fig,axs=plt.subplots(1,2,figsize=(13,6.4))
for ax,k,other,title in [(axs[0],'GEMM_WEIGHT','VECTOR_A','权重读取：实际组合单元位置'),(axs[1],'VECTOR_WRITE','GEMM_WRITE','VECTOR 写回：实际组合单元位置')]:
 ax.scatter(base[:,0],base[:,1],s=.08,c='#e4e7ec',rasterized=True)
 common={x[0] for x in pc[k]}&{x[0] for x in pc[other]}
 for shared,color,label in [(True,'#549b9e','也在另一条通路上'),(False,'#d07846','本图通路中的其余单元')]:
  points=[((r[2][0]+r[2][2])/4000,(r[2][1]+r[2][3])/4000) for r in pc[k] if (r[0] in common)==shared]
  if points:
   xy=np.array(points);ax.scatter(xy[:,0],xy[:,1],s=.7,c=color,label=label,rasterized=True)
 ss=np.array([states[n] for n,p,i in ev[k]['state_pins'] if n in states]);ax.scatter(ss[:,0],ss[:,1],s=3,c='#343b6c',label='所选数据寄存器',rasterized=True)
 ax.set_title(title,loc='left',fontweight='bold');ax.set_aspect('equal');ax.set_xlim(0,2234.91);ax.set_ylim(0,2234.91);ax.set_xlabel('X（μm）');ax.set_ylabel('Y（μm）');ax.legend(loc='upper center',bbox_to_anchor=(.5,-.14),fontsize=8,markerscale=3)
fig.text(.08,.025,'点表示最终 ODB 单元的实际中心，不是路由线或完整模块区域。左图共享比较对象为 VECTOR 读口 0；右图为 GEMM 写回。',fontsize=9,color='#546176')
fig.tight_layout(rect=[0,.08,1,1]);save(fig,'04-path-placement')

def ports(module):
 s=(SRC/'sources'/(module+'.sv')).read_text(encoding='utf8');s=re.split(r'\bmodule\s+'+module+r'\b',s,maxsplit=1)[1].split(');',1)[0];rows=[]
 for direction,typ,w,name in re.findall(r'^\s*(input|output)\s+(logic|instr_words_t|sram_req_t)\s*(\[[^\]]+\])?\s*(\w+)',s,re.M):
  width={'logic':1,'instr_words_t':512,'sram_req_t':26}[typ]
  if w:
   a,b=map(int,w[1:-1].split(':'));width=abs(a-b)+1
  rows.append(dict(direction=direction,name=name,width=width))
 return rows
portdata={m:ports(m) for m in ['gemm_engine','vec_engine']}
(P/'declared_ports.json').write_text(json.dumps(portdata,ensure_ascii=False,indent=2),encoding='utf8')
assert sum(x['width'] for x in portdata['gemm_engine'] if x['direction']=='input')==3080
assert sum(x['width'] for x in portdata['vec_engine'] if x['direction']=='input')==1576

def table(head,rows):return '<div class="table-scroll"><table><thead><tr>'+''.join('<th>'+html.escape(str(x))+'</th>' for x in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def fig(name,caption):return f'<figure><a href="{name}.png"><img src="{name}.png" alt="{html.escape(caption)}" loading="lazy"></a><figcaption>{caption}</figcaption></figure>'
def details(title,content):return '<details><summary>'+title+'</summary>'+content+'</details>'
def pct(k):return f"{R[k]['M4plus_pct']:.2f}%"
summarytable=table(['数据通路','物理网数','整网线长之和（mm）','M4 及以上'],[[s,f"{R[k]['nets']:,}",f"{R[k]['length_um']/1000:,.2f}",pct(k)] for k,s in zip(KEYS,SHORT)])
cover=table(['通路','具名数据寄存器覆盖','bank 数据引脚覆盖','实际追踪范围'],[[s,f"{D['coverage'][k]['state_cells_on_path']:,} / {D['coverage'][k]['state_cells']:,}",f"{D['coverage'][k]['ends_reached'] if k.endswith('WRITE') else D['coverage'][k]['starts_reaching_end']:,} / 2,048",desc] for k,s,desc in zip(KEYS,SHORT,['bank 读输入 → 两份权重缓冲的 D','bank 读输入 → prod、rq_m、rq_s、bias_v 的 D','bank 读输入 → FIFO 0 和分段保持寄存器的 D','bank 读输入 → FIFO 1 和分段保持寄存器的 D','两项输出 FIFO 的数据 Q／QN → bank 写输出','256 个结果寄存器的数据 Q／QN → bank 写输出'])])
layerrows=list(csv.DictReader((P/'layer_statistics.csv').open(encoding='utf-8-sig')))
layerdetail=table(['通路','金属层','线长（μm）','该层有线长的网数','每网该层均长（μm）','最小—最大（μm）'],[[D['labels'][x['group']],x['layer'].replace('metal','M'),f"{float(x['length_um']):,.2f}",x['nets'],f"{float(x['mean_um']):.2f}",f"{float(x['min_um']):.2f}—{float(x['max_um']):.2f}"] for x in layerrows if x['group'] in KEYS])
overlap=table(['共享的两条通路','共同物理网数','共同整网线长（mm）'],[[x,f"{v['nets']:,}",f"{v['length_um']/1000:,.2f}"] for x,v in D['overlap'].items()])


body='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>llaccel：模块接口与存储通路</title><style>
:root{--ink:#24364c;--muted:#617188;--line:#dce4ed;--blue:#24638c}*{box-sizing:border-box}html{scroll-behavior:smooth}body{font:16px/1.75 "Microsoft YaHei",sans-serif;color:var(--ink);background:#f1f5fa;margin:0}main{max-width:1320px;margin:32px auto;padding:0 24px 48px}header,section{background:white;border:1px solid var(--line);border-radius:14px;padding:28px 32px;margin:20px 0}h1{font-size:32px;line-height:1.4;margin:6px 0 16px}h2{font-size:24px;line-height:1.5;margin:0 0 18px}h3{font-size:19px;margin:24px 0 8px}p{margin:10px 0}a{color:var(--blue)}.eyebrow{color:var(--blue);font-size:14px;letter-spacing:1px}.note{background:#eef6fa;border-left:4px solid #4989a8;padding:14px 18px;margin:16px 0}.caution{background:#fff8e9;border-left-color:#c5903e}.muted,figcaption{color:var(--muted);font-size:14px}nav{display:flex;gap:10px 20px;flex-wrap:wrap;margin-top:18px}nav a{text-decoration:none}figure{margin:24px 0}figure img{display:block;width:100%;height:auto;border:1px solid #e7ecf2;border-radius:8px}figcaption{padding:10px 4px}.table-scroll{overflow-x:auto;margin:16px 0}table{border-collapse:collapse;width:100%;font-size:14px;white-space:normal}th,td{border-bottom:1px solid var(--line);padding:11px 13px;text-align:left;vertical-align:top}th{background:#f3f7fb;font-weight:600}tr:last-child td{border-bottom:0}details{border:1px solid var(--line);border-radius:9px;padding:12px 16px;margin:18px 0}summary{cursor:pointer;color:var(--blue);font-weight:600}code{overflow-wrap:anywhere;background:#f3f6fa;padding:2px 4px;border-radius:4px}ul{padding-left:24px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:20px}.card{border:1px solid var(--line);border-radius:9px;padding:18px}.card h3{margin:0 0 10px}@media(max-width:760px){main{padding:0 12px}header,section{padding:20px 16px}.pair{grid-template-columns:1fr}h1{font-size:26px}table{min-width:650px}}@media print{body{background:white}main{max-width:none;margin:0}section,header{break-inside:avoid;border:none}nav{display:none}}
</style></head><body><main><header><div class="eyebrow">模块、接口与完整访存连接 · Nangate45 · 2026-10-20</div><h1>llaccel：GEMM、VECTOR 如何连接 SRAM</h1><p>沿用 openTPU 的问题：模块接收什么、输出什么？接口附近的线与延伸到存储边界的线，分别用了哪些金属层？</p><div class="note"><strong>本次已完成实际连接追踪。</strong>六组通路的 M4 及以上线长占比为 59.33%～78.76%。GEMM 权重和 VECTOR 读取的寄存器端几乎全是 M2／M3；VECTOR 写回寄存器端却已有大量高层连线。</div><nav><a href="#scope">范围与结构</a><a href="#ports">模块接口</a><a href="#paths">完整通路</a><a href="#bank">对外功能与金属层</a><a href="#placement">实际单元分布</a><a href="#meaning">如何解释</a><a href="#evidence">复核依据</a></nav></header>
<section id="scope"><h2>1. 先确定：这份版图包括什么</h2><figure><img src="07-llaccel-system.svg" alt="llaccel 核心与外部 SRAM 存储体的连接边界"><figcaption>GEMM、VECTOR、ATTENTION 和 DMA 共用一个 SRAM crossbar；图中的方块是逻辑关系示意。</figcaption></figure><p><strong>当前对象是 llaccel_core。</strong>16 个 bank 的存储体在核心之外，核心内部完成请求仲裁、地址分发、写数据选择和读数据拼接。本次只能统计到真实 bank 引脚，不能继续统计 SRAM 宏内部，也不能推断宏与引擎之间的摆放距离。</p><p>与 openTPU 作职能比较时，GEMM 类似 MXU，VECTOR 类似 VPU；SRAM crossbar 类似 TMEM 中负责连接与仲裁的部分。<strong>crossbar 本身不是存储器，不能把它直接等同于整个 TMEM。</strong></p></section>
<section id="ports"><h2>2. 把两个引擎当作黑箱：有哪些输入输出</h2><div class="pair"><div class="card"><h3>GEMM：矩阵乘、累加与输出处理</h3><p>16 × 16 个 INT8 乘法单元配合求和与累加状态。权重按 256 B 的块装入双缓冲，A 按 16 B 的行流入；输出经过偏置、再量化，再写回 SRAM。</p><p>当前配置 <code>EPILOGUE_FUSION=0</code>。A 读取口也用来读取再量化参数和偏置，不能全标成“激活数据”。</p></div><div class="card"><h3>VECTOR：向量与非线性处理</h3><p>16 个通道，包含共享计算和归约逻辑。RTL 支持 RMSNorm、RoPE、SiLU、乘、加、量化等操作；从两个读口取操作数，经结果寄存器写回。</p><p>512 bit 是存储接口的声明宽度。本实现的操作数拆分器接收低 256 bit，结果保持也是 256 bit；不能据接口名推断每次都处理 512 bit 有效数据。</p></div></div>
'''
body+=table(['功能','GEMM','VECTOR','这些位做什么'],[
 ['读取数据','权重 2048 bit；A／参数 512 bit','两个读口，各 512 bit','2048 bit = 256 B；512 bit = 64 B，是一次传输的数据容器'],
 ['读取请求','每个读口：请求有效 1 bit + 地址／尺寸 26 bit','同左','26 bit = 24 位字节地址 + 2 位传输尺寸编码'],
 ['读取返回控制','每个读口：允许访问 1 bit + 返回有效 1 bit','同左','grant 表示本周期接受；rvalid 表示读数据有效'],
 ['结果写入','数据 512 bit + 字节掩码 64 bit','同左','当前输出有效数据最多 256 bit，其余补零；掩码决定哪些字节实际写入'],
 ['写请求与确认','有效 1 bit + 地址／尺寸 26 bit；输入 grant 1 bit','同左','请求未获允许时，发送者需要保持请求'],
 ['任务输入','指令 512 bit + 指令有效 1 bit','同左，另有 pos 32 bit','指令包含操作、地址、尺寸等；pos 用于位置相关运算'],
 ['任务状态','ready、busy、done 各 1 bit；完成标签 8 bit','同左','可接新任务、忙、完成，以及完成的同步信号编号'],
 ['时钟／复位与统计','clk、rst_n 各 1 bit；统计脉冲输出 5 bit','clk、rst_n 各 1 bit；统计脉冲输出 2 bit','统计脉冲不是结果数据'],
 ['声明接口总位数','输入 3080 bit；输出 673 bit','输入 1576 bit；输出 670 bit','含时钟、复位、状态和统计信号；不代表全部保留为独立物理线']])
for module,title in [('gemm_engine','GEMM'),('vec_engine','VECTOR')]:
 body+=details(title+'：展开全部 RTL 端口',table(['方向','端口','声明位宽'],[[x['direction'],f"<code>{x['name']}</code>",x['width']] for x in portdata[module]]))
body+='''<p class="muted">16 个 bank 每个提供 128 bit，合计 2048 bit。十个逻辑请求口按 bank 冲突仲裁；访问互不冲突的 bank 才能并行。GEMM 的整块权重读取占用全部 16 个 bank，不能把各引擎端口位宽直接相加当成并行带宽。</p></section>
<section id="paths"><h2>3. 从实际数据状态追踪到 bank：完整通路用了哪些层</h2><div class="note caution"><strong>这里有意不称为“恢复后的原始接口线”。</strong>综合网表没有保留大量原始端口线名。我们使用仍可确认的数据寄存器 D／Q 引脚作为起止点，沿组合逻辑追踪到 bank 引脚；不越过寄存器，也不把时钟、复位算作数据。</div>'''
body+=summarytable+fig('01-path-layers','左侧是整网线长之和，采用线性坐标；右侧按同一通路的线长归一化。每项包含多条并行物理网，不能解释成一根线有几米长。')
body+='''<p><strong>GEMM A／参数通路包含部分计算逻辑。</strong>其中 A 数据直接进入乘法组合逻辑，再由 <code>prod</code> 寄存器保存；参数和偏置进入各自寄存器。其 59.33% 不能当作“纯 crossbar 读取”的比例，也不能与其他项的绝对线长直接比较访存开销。</p>'''
body+=fig('02-scope-comparison','三个统计范围是包含关系，不能相加。寄存器端连线表示真实 D／Q 所接整网，不表示一段人为裁剪的局部路线；经过缓冲器扩展的线也可能很长。')
body+='''<p>GEMM 权重读取：寄存器直接接线的 M4 及以上仅 <strong>0.02%</strong>，整个所追踪通路升为 <strong>69.36%</strong>。VECTOR 两个读口也是寄存器端 0%，整个通路分别为 <strong>73.84%</strong>、<strong>72.53%</strong>。</p><p><strong>VECTOR 写回是另一种情况：</strong>结果寄存器直接接线就有 <strong>89.38%</strong> 的线长在 M4 及以上，经过 BUF／INV 延伸后为 <strong>88.06%</strong>，整个通路为 <strong>78.76%</strong>。因此，逻辑上刚离开一个模块或寄存器的线，也可能已经承担长距离分发。</p>'''
body+=details('展开端点覆盖与追踪范围',cover+'<p class="muted">4096 个权重寄存器对应两份 2048 bit 权重缓冲。每个 VECTOR 读取组包含 1024 个 FIFO 数据寄存器和 128 个分段保持寄存器。GEMM 写回使用两项 FIFO 各 256 bit 的数据部分，明确排除了 FIFO 中的地址位。输出寄存器 Q 与 QN 都按实际模型检查，未参与路径的互补输出不算数据位缺失。全部所选数据寄存器均至少有一个数据输出／输入连接到对应 bank 边界。</p>')
body+=details('展开每条通路逐层线长、均值与范围',layerdetail+'<p class="muted">样本为每条物理网在某一金属层上的总长，均值和范围只统计该层有正线长的网；不是几何线段长度分布。</p>')
body+='''<h3>共享很多，不能当成各模块的独占布线</h3><p>GEMM 与 VECTOR 写回共同涉及 <strong>974.02 mm</strong> 的整网线长；它占 GEMM 写回视图约 <strong>84.84%</strong>，占 VECTOR 写回视图约 <strong>66.79%</strong>。它们经过共同的 bank 输出网络，重叠并不是两个模块各自拥有一份同样的线。</p><p>四组读取也共享 bank 输入分发。所有 2048 个 bank 读数据引脚都能通过选择逻辑连向每组所选读状态；这表示选择不同 bank 时的结构可能性，不表示每个读口同时接收 2048 bit，也不表示这些连接在一个周期中全部有效。</p>'''
body+=details('展开不同通路的共同物理网',overlap)
body+='</section><section id="bank"><h2>4. 只看核心对外引脚：按功能统计金属层</h2><p>这一视角的边界最明确：读取数据、写入数据、地址、字节掩码和使能分别统计。<strong>这里只统计直接接在顶层 bank 引脚上的物理网，不把中间缓冲级一起展开。</strong>表中的金属层是走线所在层，不是引脚形状所在层。</p>'
body+=table(['对外功能','实际物理网数','声明位数','直接整网线长（μm）','M4 及以上'],[[name,f"{R[k]['nets']:,}",bits,f"{R[k]['length_um']:,.2f}",pct(k)] for k,name,bits in [('bank_rdata','bank 读数据 → 核心',2048),('bank_wdata','核心 → bank 写数据',2048),('bank_addr','bank 地址',256),('bank_we','bank 字节写掩码',256),('bank_en','bank 使能',16)]])
body+=fig('03-bank-functions','这是功能分开的“边界直接连线”统计，与完整通路视角有重叠，不能相加。读取数据和写入数据的 M4 及以上分别为 85.15% 和 79.89%。')
body+='''<p>地址和控制线的数量及直接总线长比数据线小。这个结果只描述当前引脚与放置结果；没有 SRAM 宏位置和时序数据，不能据此推出这些控制信号天然更近、更快，或者不需要长距离互联。</p></section><section id="placement"><h2>5. 实际参与通路的单元分布</h2>'''
body+=fig('04-path-placement','来自最终 ODB 单元坐标。颜色表示参与本次连接追踪，不表示恢复出了整个 crossbar 或某个原始 RTL 模块的完整物理边界。')
body+='''<p>crossbar 的组合网络在综合后大量变成匿名标准单元。旧分类中只有少量仍保留 <code>u_xbar</code> 名称的单元，不能据此认为 crossbar 只有几个门。本次从真实 bank 数据引脚与具名数据状态之间反向、正向相交，恢复了这些访存通路参与的组合单元。</p></section><section id="meaning"><h2>6. 与 openTPU 放在一起，应怎样理解</h2>'''
body+=table(['问题','llaccel 的本次结论'],[
 ['能否按模块接口分析？','可以。RTL 说明任务、数据、地址和握手的用途；物理连接追踪补上匿名逻辑与金属层统计。'],
 ['模块之间的线一定更高层吗？','不是由模块名称决定。读取状态旁的直接连接可能很短，但共享分发使用高层；VECTOR 写回寄存器的直接接线本身也偏高层。'],
 ['为什么 2048 bit bank 总线能服务多个较窄读口？','16 个 bank 每个 128 bit，经选择与拼接形成读口需要的数据；共享物理网会出现在多个功能视图中。'],
 ['是否和 TMEM 一样能追到 SRAM 宏？','当前不能。openTPU 的 TMEM 包含实际宏；这份 llaccel_core 版图止于 bank 引脚。'],
 ['能否把这些线长当成性能指标？','不能。需要实际活动、寄存器周期、时序和负载分析；本报告是物理连接与线长的结构统计。'],
 ['与 openTPU 的百分比可以直接排名吗？','需先统一端点。这里使用数据寄存器 D／Q，openTPU 先前有原始模块接口与 SRAM 宏端点；GEMM A 路径还包含乘法逻辑。']])
body+='''</section><section id="evidence"><h2>7. 证据、校验与可复现数据</h2><p>使用现有冻结的最终 ODB 提取结果；未重跑布局布线，未改动主报告。共检查 998,787 个非填充单元、1,216,339 条物理网和 2,258,123 条门内组合依赖。全局线长仍为 <strong>27,102,416.200 μm</strong>，与原提取一致。</p><ul><li>所有参与建图的标准单元都有 Liberty 模型；零个因多驱动而拒绝的组合连接。</li><li>组合门按照输出函数中的实际输入依赖追踪；MUX 只从 A／B 数据脚穿过，不从选择脚 S 穿过。</li><li>不越过任何寄存器；时钟、复位不参与数据路径。bank 存储体位于本次版图之外。</li><li>正向可达与反向可达取交集，得到从所选起点到终点的结构可能通路；未做逐周期仿真或信号条件化时序验证。</li><li>每条通路内部每个物理网只计一次；整条电气网的所有路由分支都计长，并未把同一网的分支按用途分摊。因此“在通路上”不等于全部线长由该通路独占。</li></ul>'''
body+=details('展开源码、输入和统计文件',f'''<p>ODB SHA256：<code>{D['source']['extraction']['odb_sha256']}</code></p><p>配置：<code>EPILOGUE_FUSION=0</code>，<code>DMA_MAX_OUTSTANDING=16</code>；源码快照 <code>{D['source']['source_commit']}</code>。</p><p><a href="summary.json">完整统计与方法</a> · <a href="layer_statistics.csv">逐层线长、均值和范围 CSV</a> · <a href="declared_ports.json">RTL 端口位宽</a> · <a href="endpoint_evidence.json">具名寄存器端点</a> · <a href="path_net_evidence.jsonl.gz">物理网编号与分组</a> · <a href="path_cells.json.gz">通路实际单元坐标</a> · <a href="sram_xbar.sv">crossbar RTL 副本</a> · <a href="liberty_models.json">门功能模型</a></p><p><a href="analyze_paths.py">连接追踪脚本</a> · <a href="build_llaccel_section.py">图表与 HTML 生成脚本</a> · <a href="../../llaccel-engine-analysis-20261020/llaccel引擎分析.html">另见：已有引擎内部布局与功能细分分析</a></p><p class="muted">输入依赖同级目录 <code>llaccel-engine-analysis-20261020/compact_physical_evidence.jsonl.gz</code>。主报告和线长报告均未修改。</p>''')
body+='</section></main></body></html>'
from bs4 import BeautifulSoup
fragment=BeautifulSoup(body,'html.parser')
(P/'sections.json').write_text(json.dumps({'sections':[str(x) for x in fragment.select('main > section')]},ensure_ascii=False),encoding='utf8')
print('Built llaccel section fragments and charts for the combined module/interface report.')
