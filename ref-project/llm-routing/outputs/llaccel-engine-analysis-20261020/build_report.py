"""Render measured scientific figures and a self-contained local HTML study."""
from pathlib import Path
from collections import Counter,defaultdict
import csv,gzip,json,hashlib,html,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.collections import PolyCollection
from matplotlib.patches import Patch

P=Path(__file__).resolve().parent
S=json.loads((P/'summary.json').read_text(encoding='utf8'))
G=S['groups']; E=['GEMM','ATTENTION','VECTOR']; L=['metal'+str(i) for i in range(1,11)]
ROWS=list(csv.DictReader((P/'layer_lengths.csv').open(encoding='utf-8-sig')))
PAIRS=list(csv.DictReader((P/'group_connections.csv').open(encoding='utf-8-sig')))
LABEL={g:values[0] for g,values in G.items()}
ENGINE_NAME={'GEMM':'矩阵计算引擎（GEMM）','ATTENTION':'注意力引擎（ATTENTION）','VECTOR':'向量引擎（VECTOR）'}
for font_file in ('C:/Windows/Fonts/msyh.ttc','C:/Windows/Fonts/msyhbd.ttc'):
 if Path(font_file).exists():font_manager.fontManager.addfont(font_file)
plt.rcParams.update({'font.family':['Microsoft YaHei','DejaVu Sans'],'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','savefig.facecolor':'white','axes.unicode_minus':False})
def num(x):return f'{x:,.3f}'
def pct(n,d):return 100*n/d if d else 0
def save(fig,stem):
 fig.savefig(P/(stem+'.png'),dpi=190,bbox_inches='tight')
 plt.close(fig)
 print(stem,flush=True)
def group_keys(e):return [k for k in G if k.startswith(e+'.')]
def table(headers,rows):return '<div class="table-scroll"><table><thead><tr>'+''.join('<th>'+html.escape(str(h))+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(v)+'</td>' for v in r)+'</tr>' for r in rows)+'</tbody></table></div>'
def image(stem,caption):return f'<figure><a href="{stem}.png"><img loading="lazy" src="{stem}.png" alt="{html.escape(caption)}"></a><figcaption>{caption}</figcaption></figure>'

def placements():
 data={e:defaultdict(list) for e in E}
 with gzip.open(P/'cell_assignments.jsonl.gz','rt',encoding='utf8') as f:
  for line in f:
   name,master,box,g,tier,mask=json.loads(line);e=g.split('.')[0]
   if e in E:data[e][g].append((box,tier in ('SOURCE','NAMED_NET')))
 for e in E:
  fig,ax=plt.subplots(1,2,figsize=(15.5,8.0),sharex=True,sharey=True)
  for aa in ax:
   aa.set_facecolor('#f0f1f3');aa.set_xlim(0,2234.91);aa.set_ylim(0,2234.91);aa.set_aspect('equal')
   aa.set_xlabel('横坐标（物理微米）')
  ax[0].set_ylabel('纵坐标（物理微米）')
  for g in group_keys(e)+[e+'.SHARED']:
   values=data[e].get(g,[])
   if not values:continue
   boxes=np.array([v[0] for v in values],dtype=float)/2000
   anchors=np.array([v[1] for v in values],dtype=bool)
   poly=np.stack([boxes[:,[0,1]],boxes[:,[2,1]],boxes[:,[2,3]],boxes[:,[0,3]]],axis=1)
   color=G[g][1] if g in G else '#9c8e83'
   for j,sel in [(0,anchors),(1,np.ones(len(values),dtype=bool))]:
    ax[j].add_collection(PolyCollection(poly[sel],facecolors=color,edgecolors='none',rasterized=True))
  left_count=sum(v['SOURCE']+v['NAMED_NET'] for g,v in S['tier_counts'].items() if g.startswith(e+'.'))
  right_count=sum(v for g,v in S['cell_counts'].items() if g.startswith(e+'.'))
  ax[0].set_title(f'源码可直接定位的单元（{left_count:,} 个）',pad=12)
  ax[1].set_title(f'加入连接推断后的功能分布（{right_count:,} 个）',pad=12)
  handles=[Patch(facecolor=G[g][1],label=f'{LABEL[g]}（{S["cell_counts"].get(g,0):,}）') for g in group_keys(e)]
  shared=S['cell_counts'].get(e+'.SHARED',0)
  handles.append(Patch(facecolor='#9c8e83',label=f'多个内部组共享（{shared:,}）'))
  fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.005),ncol=3,frameon=False,fontsize=9.5)
  fig.suptitle('llaccel｜'+ENGINE_NAME[e]+'功能布局',fontsize=20,fontweight='bold',y=.98)
  fig.text(.5,.925,'同一份最终布局，位置未变；灰底隐藏其他单元，不表示空白区域或未知功能。图例数量对应右图。',ha='center',fontsize=10,color='#475569')
  fig.subplots_adjust(top=.88,bottom=.23,wspace=.13)
  save(fig,e.lower()+'_placement')

def layer_figures(e):
 keys=group_keys(e);mat=np.zeros((len(keys),10))
 for r in ROWS:
  if r['scope']=='INTERNAL' and r['group'] in keys and r['layer'] in L:
   mat[keys.index(r['group']),L.index(r['layer'])]=float(r['length_um'])
 fig,ax=plt.subplots(1,2,figsize=(16,7.5))
 x=np.arange(10);w=.8/len(keys)
 for i,g in enumerate(keys):
  pos=mat[i]>0
  ax[0].bar((x-.4+i*w+w/2)[pos],mat[i][pos],width=w,color=G[g][1],label=LABEL[g])
 ax[0].set_yscale('log');ax[0].set_ylabel('整网中心线长度（物理微米，对数坐标）')
 ax[0].set_title('各功能组在各层的绝对线长')
 total=mat.sum(axis=0);bottom=np.zeros(10)
 for i,g in enumerate(keys):
  a=np.divide(mat[i]*100,total,out=np.zeros(10),where=total>0)
  ax[1].bar(x,a,bottom=bottom,color=G[g][1],width=.7);bottom+=a
 for i,t in enumerate(total):
  if t==0:ax[1].text(i,2,'0',ha='center',color='#64748b')
 ax[1].set_ylim(0,105);ax[1].set_ylabel('占同层已分细组内部线长的比例（%）')
 ax[1].set_title('每一金属层内的功能构成')
 for aa in ax:
  aa.set_xticks(x,['M'+str(i) for i in range(1,11)]);aa.set_xlabel('金属层（M1 为第 1 层）');aa.grid(axis='y',alpha=.18);aa.set_axisbelow(True)
 fig.legend(handles=[Patch(facecolor=G[g][1],label=LABEL[g]) for g in keys],loc='lower center',bbox_to_anchor=(.5,.005),ncol=3,frameon=False)
 fig.suptitle('llaccel｜'+ENGINE_NAME[e]+'逐层功能线长',fontsize=19,fontweight='bold')
 fig.text(.5,.91,'仅计全部物理端点属于同一细组的网；组间、共享及端点未完整分组的网另行统计。',ha='center',fontsize=9.5,color='#475569')
 fig.subplots_adjust(top=.83,bottom=.25,wspace=.22)
 save(fig,e.lower()+'_layers')

def connection_figure(e):
 totals=Counter(S['group_pair_totals_dbu'][e]);pairs=[p for p,v in totals.most_common(12)]
 fig,ax=plt.subplots(figsize=(14,max(5.2,.42*len(pairs)+2.0)))
 bottom=np.zeros(len(pairs));colors=plt.cm.viridis(np.linspace(.12,.9,10))
 for li,layer in enumerate(L):
  a=np.array([sum(float(r['length_um']) for r in PAIRS if r['engine']==e and r['pair']==p and r['layer']==layer)/1000 for p in pairs])
  if a.any():ax.barh(np.arange(len(pairs)),a,left=bottom,color=colors[li],label='M'+str(li+1));bottom+=a
 labels=['\n↔ '.join(LABEL[g] for g in p.split(' ↔ ')) for p in pairs]
 ax.set_yticks(np.arange(len(pairs)),labels);ax.invert_yaxis();ax.set_xlabel('整网中心线长度（千物理微米）')
 ax.set_title(ENGINE_NAME[e]+'｜主要内部组间连接',pad=18,fontsize=16)
 ax.grid(axis='x',alpha=.16);ax.set_axisbelow(True);ax.legend(loc='upper center',bbox_to_anchor=(.5,-.14),ncol=10,frameon=False)
 fig.text(.5,.02,'仅计端点完整且恰好涉及两个细组的网；每网计一次整网线长，不代表某条路由分支或专用总线长度。',ha='center',fontsize=9,color='#475569')
 fig.subplots_adjust(left=.40,right=.97,top=.88,bottom=.23)
 save(fig,e.lower()+'_connections')

MANUAL={
 'GEMM':{
 'lead':'矩阵计算引擎（GEMM）采用 16×16 路 8 位整数乘法和 16 路求和归约，结果写入 16×16 个 32 位累加状态。它没有 Gemmini 那种二维相邻处理单元（PE）逐跳传递的网格结构，不能按处理单元网格解释本图。',
 'flow':'权重双缓冲＋激活读口 → 乘法级 → 求和级 → 累加状态 → 偏置／再量化 → 输出先进先出队列（FIFO）→ 静态存储互连',
 'notes':[
  '“乘法级”含乘法输入选择、乘法逻辑、结果寄存器以及只连向该级的辅助逻辑；“累加状态”含寄存器、读写选择和反馈。图中不是每个点一个乘法器，一个乘法位置由许多标准单元实现。',
  '本次 EPILOGUE_FUSION=0，未启用可选的融合激活／残差尾处理；偏置、缩放、舍入、饱和及结果流水仍然存在。因此，尾部组线长较大不能解释成“启用了额外融合算子”。',
  '左图只显示保留名称的单元；右图加入沿输出连接追踪、且只连向一个组的匿名逻辑。权重寄存器到乘法级的线路被分在组间，不能用“权重组内线长”代替全部权重分发成本。'],
 'anchors':[
 ('WEIGHT','wbuf[2]、wbuf_valid、ld_*、w_ptr','4096 位权重双缓冲及装载状态；不包括跨到乘法组的线路'),
 ('MULTIPLY','prod[16][16]、p_valid、p_m','256 个乘法结果位置，共 4096 位结果寄存器及其前级逻辑'),
 ('REDUCE','psum[16]、s_valid、s_m','16 路、每路 20 位的求和结果及其前级归约'),
 ('ACC','acc[16][16]','8192 位累加状态及只连向这些状态的选择／反馈逻辑'),
 ('EPILOGUE','bias_v、rq_m、rq_s、d1_val、d2_p、d3_*、d4_*','偏置、缩放、移位与饱和流水；也包含对应保持、选择与控制'),
 ('OUTPUT','u_out、out_ptr、out_nt_base、wr_ph','输出队列、输出地址流水和拆分写回'),
 ('CONTROL','其余 u_gemm.* 命名状态','指令、A 读口地址、循环、响应标签、调度；不是纯布尔控制门数量')],
 'source':'gemm_engine.sv'},
 'ATTENTION':{
 'lead':'注意力引擎（ATTENTION）使用 64 条算术通道处理最多 256 维的注意力头，较宽的注意力头分组复用。查询数据 Q 保持在本地寄存器，键／值数据 K/V 从外部动态存储器（DRAM）分段取回；256 项分数缓冲先存分数、后存概率，最后对 V 加权累加并输出。',
 'flow':'Q 保持 ＋ K 分段取回 → 点积 → 分数缓冲 ↔ 最大值／指数近似／归一化 → 概率×V → 累加 → 再量化／写回队列',
 'notes':[
  'K/V 组主要是请求标签、响应拼接和一行数据的保持，不是完整键值缓存。完整 K/V 数据在核心外的 DRAM，本布局没有把外部存储体画进来。',
  '输出组同时承担 ATTENTION 结果写回与 KV_WRITE 的写队列。组中含多路结果选择、再量化、队列和端口拆分，不能视作一段无计算的“出口连线”。',
  '分数／概率组包含 sbuf 的读写选择。概率归一化（softmax）组包含最大值、指数查表近似、求和和除法；p_val 等保留信号作为组合逻辑边界补充依据。这能细分部分匿名逻辑，但并不证明完整的算子物理边界已经恢复。'],
 'anchors':[
 ('Q','qv、qrow、q_issued','2048 位 Q 保持及请求状态'),
 ('KV','u_dram_tags、dram_*、row_asm、key_row、rd_ph、rsp_*','请求跟踪、分段响应拼接、K 行保持与相关地址状态'),
 ('DOT','dot、dot_partial、s_reg、s_t、s_valid、k_group','点积和多组归约；dot 保留网名提供少量组合输出依据'),
 ('SCORE','sbuf、s_rd','256×32 位分数／概率状态及前级写入、选择逻辑'),
 ('SOFTMAX','mx、z_big、z_lo、sum、inv_r、u_udiv、p_val、p_prod','最大值、指数近似、求和与归一化；含组合信号边界'),
 ('VALUE','o、pn_q、v_q、vv、v_group、pn_prod','256×32 位累加状态、V 保持和加权计算'),
 ('OUTPUT','wdata_acc、og、Mo_r、So_r、u_wq、wr_ph、dst_*','结果再量化、两项写队列与写端口拆分，也服务 KV_WRITE'),
 ('CONTROL','其余 u_attn.* 命名状态','指令、注意力头／词元循环、多轮处理和通用地址调度')],
 'source':'attn_engine.sv'},
 'VECTOR':{
 'lead':'向量引擎（VECTOR）的 16 条通道执行均方根归一化（RMSNorm）、旋转位置编码（RoPE）、SiLU 激活、逐元素运算与量化。当前按实际硬件职责分组；不同操作的选择逻辑和部分运算电路会共同落在通道计算组。',
 'flow':'双读口 → 响应拆分／FIFO → 共享通道运算 ↔ 归约／开方／除法 → 结果保持 → 写口；三组地址遍历器提供读写地址',
 'notes':[
  '“共享通道计算与结果保持”包括运算选择、定点算术、查表近似、临时结果和输出保持；线长大不等于某一个算子单独占用这些线。',
  'RMSNorm 的平方和、开方、除法和归一化状态独立标出；RoPE 的 x1/cos/y2 临时寄存器归入通道组。其他组合逻辑只能根据连接确定它服务的硬件组，无法唯一归到某条 ISA 指令。'],
 'anchors':[
 ('READ','u_f0、u_f1、u_s0、u_s1','两个响应 FIFO、跨行拆分与拼接'),
 ('NORM','ss、r_r、inv_r、norm_state、u_isqrt、u_udiv','共享平方和／开方／除法及状态'),
 ('LANES','x1_r、c_r、y2_r、wr_data_r','共享算术、临时结果与写数据保持'),
 ('ADDRESS','u_w0、u_w1、u_wc、wr_addr_r、wr_size_*、wr_ph','读口与写口的遍历、地址和拆分状态'),
 ('CONTROL','其余 u_vec.* 命名状态','操作码、标量参数、指令与通用流水控制')],
 'source':'vec_engine.sv'},
}

def engine_html(e):
 keys=group_keys(e);m=MANUAL[e]
 total=sum(float(r['length_um']) for r in ROWS if r['scope']=='ENGINE' and r['group']==e)
 ints={g:sum(float(r['length_um']) for r in ROWS if r['scope']=='INTERNAL' and r['group']==g) for g in keys}
 source=sum(v['SOURCE'] for k,v in S['tier_counts'].items() if k.startswith(e+'.'))
 named=sum(v['NAMED_NET'] for k,v in S['tier_counts'].items() if k.startswith(e+'.'))
 inferred=sum(v['RECEIVER'] for k,v in S['tier_counts'].items() if k.startswith(e+'.'))
 shared=S['cell_counts'].get(e+'.SHARED',0);allcells=source+named+inferred+shared
 ranked=sorted(ints,key=ints.get,reverse=True);g1,g2=ranked[:2]
 between=total-sum(ints.values())
 metal23=sum(float(r['length_um']) for r in ROWS if r['scope']=='ENGINE' and r['group']==e and r['layer'] in ('metal2','metal3'))
 parts=[f'<section id="{e.lower()}"><h2>{ENGINE_NAME[e]}：内部结构、布局与逐层布线</h2>',f'<p>{m["lead"]}</p>',f'<div class="flow">{m["flow"]}</div>',f'<p class="result">已分组范围：{allcells:,} 个标准单元，其中源码命名 {source:,} 个、保留信号定位 {named:,} 个、按连接追踪 {inferred:,} 个、组间共享 {shared:,} 个。<br>完整端点均能分到本引擎的信号网共 {num(total)} μm；其中 M2＋M3 为 {pct(metal23,total):.2f}%。该范围包含本引擎的共享组，不含跨引擎、端口、时钟复位及未完整归属的网。</p>']
 parts.append(image(e.lower()+'_placement',f'左右是同一份布局，位置未变。左：源码可直接定位的 {source+named:,} 个单元；右：加入连接推断后的 {allcells:,} 个单元，其中褐灰色为多个内部组共享。图例数量对应右图；灰底隐藏其他引擎、未分组单元和填充等物理单元，不表示空白区域或未知功能。'))
 parts.append('<h3>图例中的每一类具体包含什么</h3>')
 parts.append(table(['类别（与图例一致）','对应源码状态或层次','解释'],[(f'<span class="swatch" style="background:{G[e+"."+k][1]}"></span>{G[e+"."+k][0]}',html.escape(anchor),meaning) for k,anchor,meaning in m['anchors']]+[('多个内部组共享','由多组连接共同确定','能确认它连向本引擎的多个细组，保留为共享；不按位置分配给最近的一组')]))
 parts.append('<ul>'+''.join('<li>'+x+'</li>' for x in m['notes'])+'</ul>')
 parts.append('<h3>金属层与功能分布</h3>')
 parts.append(f'<p>同组内部网中，<b>{G[g1][0]}</b>为 {num(ints[g1])} μm，<b>{G[g2][0]}</b>为 {num(ints[g2])} μm；分别占上述完整引擎范围的 {pct(ints[g1],total):.2f}%、{pct(ints[g2],total):.2f}%。另有 {num(between)} μm 属于组间连线或涉及共享逻辑的网，单列后才与引擎汇总相等。</p>')
 parts.append(image(e.lower()+'_layers','左图纵轴为对数坐标，显示各层绝对线长；右图显示同一层内各功能组的比例。两图均只统计全部物理端点落在同一细组的网；零值不画对数柱。'))
 def layer_share(g,layer):
  vals={r['group']:float(r['length_um']) for r in ROWS if r['scope']=='INTERNAL' and r['group'].startswith(e+'.') and r['layer']==layer}
  return pct(vals.get(g,0),sum(vals.values()))
 if e=='GEMM':
  parts.append(f'<p><b>逐层看：</b>M2、M3 中偏置／再量化组分别占同层已分细组内部网的 {layer_share("GEMM.EPILOGUE","metal2"):.2f}%、{layer_share("GEMM.EPILOGUE","metal3"):.2f}%；乘法级分别约 {layer_share("GEMM.MULTIPLY","metal2"):.2f}%、{layer_share("GEMM.MULTIPLY","metal3"):.2f}%。到 M4、M5，求和归约的占比升至 {layer_share("GEMM.REDUCE","metal4"):.2f}%、{layer_share("GEMM.REDUCE","metal5"):.2f}%，显示归约连线在这些层比低层更突出。这里比较的是本引擎各细组的层内构成，不是整个芯片各层的使用率。</p>')
 elif e=='ATTENTION':
  parts.append(f'<p><b>逐层看：</b>M2、M3 主要落在输出处理与 V 加权累加，二者合计分别为 {layer_share("ATTENTION.OUTPUT","metal2")+layer_share("ATTENTION.VALUE","metal2"):.2f}%、{layer_share("ATTENTION.OUTPUT","metal3")+layer_share("ATTENTION.VALUE","metal3"):.2f}%。M6 的 K/V 访问／拼接组占 {layer_share("ATTENTION.KV","metal6"):.2f}%，M7 的 V 加权组占 {layer_share("ATTENTION.VALUE","metal7"):.2f}%。高层总线长较少，不能只看百分比就认定高层承担了主要开销；需要同时看左图的绝对量。</p>')
 else:
  parts.append(f'<p><b>逐层看：</b>M2、M3 的共享通道计算与结果保持组分别占 {layer_share("VECTOR.LANES","metal2"):.2f}%、{layer_share("VECTOR.LANES","metal3"):.2f}%。读响应缓冲在 M5 中占 {layer_share("VECTOR.READ","metal5"):.2f}%，在 M7 中占 {layer_share("VECTOR.READ","metal7"):.2f}%；这说明读缓冲和分发在部分高层有明显份额，并不表示它比通道计算消耗更多总线长。</p>')
 parts.append(table(['功能组','单元数','同组内部网长度（μm）','占完整引擎范围'],[(G[g][0],f'{S["cell_counts"].get(g,0):,}',num(ints[g]),f'{pct(ints[g],total):.2f}%') for g in keys]+[('组间及含共享逻辑的网','—',num(between),f'{pct(between,total):.2f}%'),('完整引擎范围合计',f'{allcells:,}',num(total),'100%')]))
 parts.append(image(e.lower()+'_connections','只展示端点完整、且恰好涉及两个细组的物理网。图中长度是整条网的总长，可能包含控制和多扇出；不等于两个算法算子之间的专用总线。'))
 parts.append('<details><summary>展开逐层平均线长、最小—最大范围与完整分组表</summary><p>均值／范围以“某条网在某金属层上的去重中心线长度”为样本，单位 μm。跨层网会在不同层各出现一次；不是单根几何线段的长度分布。表内均为同组内部网。</p>')
 parts.append(table(['功能组','金属层','网-层条目数','总线长','平均','最小—最大'],[(G[r['group']][0],'M'+r['layer'].removeprefix('metal'),f'{int(r["net_layer_entries"]):,}',num(float(r['length_um'])),num(float(r['mean_net_layer_length_um'])),f'{num(float(r["min_net_layer_length_um"]))} — {num(float(r["max_net_layer_length_um"]))}') for r in ROWS if r['scope']=='INTERNAL' and r['group'].startswith(e+'.')]))
 parts.append('</details><p class="links">依据：<a href="sources/'+m['source']+'">本次实现的 '+m['source']+'</a> · <a href="cell_counts.csv">单元计数</a> · <a href="layer_lengths.csv">逐层线长与范围</a> · <a href="group_connections.csv">组间整网逐层表</a></p></section>')
 return ''.join(parts)

def main():
 placements()
 for e in E:layer_figures(e);connection_figure(e)
 total=S['conservation']['observed_dbu']/2000
 buckets={'INTERNAL':'细组内部','BETWEEN_GROUPS':'同引擎组间','SHARED':'同引擎共享组内部','OTHER':'其他已知模块内部','CROSS_ENGINE':'完整的跨引擎／跨模块网','EXTERNAL':'完整的顶层端口网','PARTIAL':'端点未完整分组的网','DEDICATED':'时钟／复位'}
 source_sha={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in (P/'sources').glob('*.sv')}
 S['local_source_sha256']=source_sha
 (P/'source_hashes.json').write_text(json.dumps(source_sha,indent=2),encoding='utf8')
 remaining=S['cell_counts'].get('UNRESOLVED',0);cross=S['cell_counts'].get('CROSS_ENGINE_OR_EXTERNAL',0);clock=S['cell_counts'].get('DEDICATED_CLOCK_RESET',0)
 head='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>llaccel 引擎内部布局与布线分析</title><style>
 :root{color-scheme:light}*{box-sizing:border-box}body{margin:0;background:#f4f6f8;color:#1d2939;font:16px/1.8 "Microsoft YaHei",sans-serif}main{max-width:1360px;margin:24px auto;background:#fff;padding:36px 46px}h1{font-size:30px;line-height:1.4}h2{font-size:25px;border-bottom:2px solid #dbe4ef;padding-bottom:12px;margin-top:46px}h3{font-size:20px;margin-top:26px}p{margin:14px 0}nav{display:flex;gap:12px;flex-wrap:wrap}a{color:#255fa4;text-decoration:none}nav a{background:#eaf1f9;padding:5px 14px;border-radius:6px}.result,.flow{background:#edf4fb;border-left:4px solid #3974ac;padding:15px 19px;margin:20px 0}.flow{background:#f4f7fa;line-height:2}.note,figcaption,small{color:#596579}.table-scroll{overflow-x:auto;margin:16px 0}table{width:100%;border-collapse:collapse;font-size:14px}th,td{padding:10px 12px;border-bottom:1px solid #dce2e9;text-align:left;vertical-align:top}th{background:#edf1f6;white-space:nowrap}figure{margin:24px 0}figure img{display:block;width:100%;height:auto;border:1px solid #e5e9ee}figcaption{font-size:14px;margin-top:8px}details{border:1px solid #dce2e9;background:#fafbfd;padding:12px 18px;margin:20px 0}summary{font-weight:600;cursor:pointer}.swatch{display:inline-block;width:14px;height:14px;margin-right:7px;border-radius:2px}li{margin:10px 0}.links{font-size:14px}code{word-break:break-all}footer{border-top:1px solid #dce2e9;margin-top:36px;padding-top:20px;font-size:13px;color:#657286}@media(max-width:760px){main{margin:0;padding:20px 16px}h1{font-size:24px}h2{font-size:21px}table{min-width:680px}}@media print{details{display:block}main{padding:0;margin:0}figure{break-inside:avoid}body{background:white}}
 </style><main><h1>llaccel：引擎内部功能布局与逐层布线</h1><p class="note">2026-10-20 · Nangate45 工艺库 · 顶层模块 llaccel_core · 源码提交 f7db8a2 · 补充研究</p><nav><a href="#boundary">比较边界</a><a href="#gemm">矩阵计算</a><a href="#attention">注意力计算</a><a href="#vector">向量运算</a><a href="#unknown">剩余未解析部分</a><a href="#method">口径与守恒</a></nav>
 <p class="result">本报告对最终物理端点重新分组，区分矩阵计算、注意力和向量引擎的内部功能。所有细组使用相同的保守规则，并把共享、边界及未完整归属的网单列。</p>
 <p>最终作业 89069 已完成，最终网表等价检查通过。2026-10-20 核对的最终物理数据库与网表文件校验值（SHA256）均与原报告快照一致，本次沿用该真实布线数据。独立静态时序分析与归档任务尚未完成；这里的结果是物理布局和连线统计，不构成时序签核结论。</p>
 <section id="boundary"><h2>与 openTPU 怎么对照</h2><p>两个项目都能服务大语言模型推理，差别主要在硬件组织。本次物理实现比较的是 openTPU 的计算分片（slice）范围与 llaccel 的计算核心（core）范围；名称并不规定谁更高一级。矩阵计算内部最直接的对应是 openTPU 的矩阵运算单元（MXU）与这里的矩阵计算引擎（GEMM），注意力引擎（ATTENTION）、向量引擎（VECTOR）则另外展开。</p><p><b>llaccel_core 不包含静态存储器（SRAM）的存储体</b>，只保留存储互连和外部存储体端口；openTPU 案例包含 ACT_RAM、TMEM 等存储宏。不能直接根据两个完整芯片图的面积或线长占比判断存储开销高低。</p><div class="flow">命令处理器 → 数据搬运／矩阵计算／向量运算／注意力计算<br>四个引擎 ↔ 静态存储互连 ↔ 核心外的静态存储体<br>注意力引擎、数据搬运引擎（DMA）、指令取回 ↔ 动态存储访问仲裁 ↔ 外部动态存储器（DRAM）</div><p>模型层的“矩阵计算产生结果供注意力计算使用”，可能经静态存储器写入再读取实现。报告中的组间连线严格依据物理网端点；没有推断一条不存在的引擎间专用总线。</p></section>'''
 content=head+''.join(engine_html(e) for e in E)
 content+=f'<section id="unknown"><h2>剩余未解析部分究竟是什么</h2><p>本次提取了 {S["cells"]:,} 个实际单元，已排除填充、衬底接触和天线保护单元。专用时钟、复位驱动单元 {clock:,} 个单列；{cross:,} 个单元同时连向不同引擎或顶层端口，保留为跨引擎／外部共同逻辑；另有 {remaining:,} 个单元没有足够信息完整分组。</p><p>这些并不全是缓冲器。未完整分组的部分包含多路选择器、普通组合门、缓冲器和反相器等；仅知道库单元类型时，可以说明“做选择、缓冲或逻辑运算”，不能由此证明它属于哪个算法功能。</p><p>三个引擎内部仍有褐灰色共享单元：它们的输出确实能走到本引擎的多个细组。强行按相邻区域或多数接收端着色，会把共享地址、使能和多路选择逻辑误写成某个算术组，因此保留共享类别。</p><p>新图与旧报告的未解析比例不能直接相减。旧图侧重粗粒度接收引擎；这里还要求细组完整、所有物理端点完整，口径更严格。<b>一个网即使部分端点已能解释，也不会把整网强算成某个细组。</b></p></section>'
 types=Counter()
 for master,n in S['unknown_master_types'].items():
  kind='缓冲器（BUF／CLKBUF）' if master.startswith(('BUF','CLKBUF')) else ('反相器（INV）' if master.startswith('INV') else ('多路选择器（MUX）' if master.startswith('MUX') else ('未命名时序单元' if master.startswith(('DFF','SDFF','DLH','DLL')) else '其他逻辑门／算术原语')))
  types[kind]+=n
 qtable=table(['跨引擎／外部共同逻辑＋未解析单元的库类型','实际单元数','可以解释到的程度'],[(k,f'{v:,}',{'缓冲器（BUF／CLKBUF）':'信号驱动与分发；CLKBUF 是库单元名，不能仅凭此认定一定属于时钟树','反相器（INV）':'极性变换或反相信号分发','多路选择器（MUX）':'数据／地址／控制选择；无法唯一归到某个引擎','未命名时序单元':'状态保持，但没有可用的功能名称','其他逻辑门／算术原语':'逻辑组合或局部算术，需更多名称或完整连接才能确认用途'}[k]) for k,v in types.items()])
 # Insert before this section closes; other sections are already complete.
 last=content.rfind('</section>');content=content[:last]+qtable+content[last:]
 content+='<section id="method"><h2>怎么得到这些图和数字</h2><ol><li><b>源码可确认：</b>单元名保留 u_gemm、u_attn 或 u_vec 的状态／子模块名称，按源码职责分类。这里的“来源”就是综合前电路源码中的这些名称。</li><li><b>保留信号定位：</b>dot、p_val 等内部网名仍在最终网表中，用其实际驱动端确定少量组合逻辑边界。模块输入别名不作为内部来源依据。</li><li><b>按连接追踪：</b>从匿名单元输出顺着网表寻找下游依据。只有所有可追踪输出都落到一个功能组，且没有未知终点或顶层出口，才归到该组。遇到已知来源单元或寄存器就停止，不穿过寄存器把前后级混在一起。</li><li><b>线长记账：</b>使用最终物理数据库中的同网、同层去重中心线，2000 个数据库单位＝1 μm；一条网在全局分类中只计一次。按同组、组间、共享、跨引擎、外部、未完整分组和时钟复位区分。它不是时序路径长度，也不是逻辑通道吞吐量。</li></ol>'
 content+=table(['互斥类别','线长（μm）','占全芯片'],[(label,num(S['global_length_dbu'].get(k,0)/2000),f'{pct(S["global_length_dbu"].get(k,0)/2000,total):.3f}%') for k,label in buckets.items()]+[('<b>合计／与原提取核对</b>',f'<b>{num(total)}</b>','<b>100% · 一致</b>')])
 content+='<details><summary>展开复核文件、重现脚本与限制</summary><p><a href="summary.json">完整统计与输入校验值</a> · <a href="source_hashes.json">本地源码校验值</a> · <a href="live_source_receipt.json">服务器源码、作业与等价检查状态</a> · <a href="validation.json">守恒与文件检查</a> · <a href="net_anchor_evidence.json">保留信号定位证据</a> · <a href="sample_net_assignments.json">整网分组样例</a> · <a href="cell_assignments.jsonl.gz">逐单元分类</a> · <a href="analyze.py">分组与守恒脚本</a> · <a href="build_report.py">绘图／报告脚本</a></p><p>匿名逻辑的连接分组不是原电路源码层次的恢复。以整个标准单元作为最小粒度，多输出门若服务不同组就保留共享。端点不完整、多组共用、寄存器边界及未保留信号名限制了进一步细分。组合级中的选择、使能、保持与算术不能仅凭该组名字再拆开；组内线长不等于纯乘法器或纯概率归一化算术的物理成本。</p><p>未包含电源特殊线的中心线长度、宏内部、静态存储体内部或外部动态存储器实体；没有用线长推出能耗、频率、带宽和性能瓶颈。</p></details></section><footer>本地补充报告；数据来自既有最终布线数据库的只读提取。本次未启动综合／布局／布线或改动服务器任务。</footer></main></html>'
 (P/'llaccel引擎分析.html').write_text(content,encoding='utf8')
 print('report written',flush=True)

if __name__=='__main__':main()
