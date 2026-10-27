"""Publish portable Chinese HTML, figures, full pin tables and auditable sources.

Run after inventory/bind/coverage. Large immutable routed inputs remain indexed remotely.
"""
from pathlib import Path
import argparse,csv,gzip,hashlib,html,json,shutil,sys
import numpy as np
import pandas as pd
import expand_candidates as expand

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[2]
TITLES=expand.TITLES
ORDER=['act','mxu','opentpu_aux','gemm','vector','llaccel_aux']
RECOMMEND={
 'act':'优先做 C 的稀疏局部试验。数据/scale 组有真实内部端点依据；时钟和窄控制留边。全 C 仍有145个异网直接相交 pin，需接入修复。',
 'mxu':'保留边界和 C 局部试验并行。C 的端点 L1 减少有限；t_wdata/t_wen 按真实32-bit lane 关联，ACT 链路优先靠相关 FIFO/逻辑。',
 'opentpu_aux':'采用混合式少量内移。TMEM、VPU、DMA/量化局部端点提供候选中心；外部 DRAM/collective、控制和共享信号保留边缘更合理。',
 'gemm':'优先 C 数据簇的局部试验。288个恒零高位写数据/strobe 保留，不能据逻辑常量随意删 pin。全 C 冲突260个，不具备直接替换资格。',
 'vector':'本轮推荐优化原边界。B/C 的端点 L1 都增加，迁移价值有限；即使内部窗口几何可放，也不能据此主张收益。',
 'llaccel_aux':'先优化边界并按真实 bank/事务局部试验。全 C 的4731个直接金属相交 pin、6700个基础间距风险提示拥塞可能向内部转移；不建议整体采用。'}

def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
def compress(src,dst):
    with dst.open('wb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as f:f.write(src.read_bytes())
def table(df):return df.to_html(index=False,escape=True,border=0,classes='stats')

def endpoint_plot(root,c):
    legacy=expand.legacy;legacy.ROOT=root
    d=pd.read_csv(root/f'{c}_pin_coordinates.csv',low_memory=False)
    a=d[d.plan=='A'].reset_index(drop=True);cc=d[d.plan=='C'].set_index('pin').loc[a.pin].reset_index()
    raw=pd.read_csv(root/'physical'/c/'anchors.tsv.gz',sep='\t');raw.pin=raw.pin.map(legacy.norm)
    anchor={p:g[['x','y']].to_numpy(float)/2000 for p,g in raw.groupby('pin')}
    m=json.loads((root/f'{c}.meta.json').read_text());dims=np.array(m['die_dbu'])/2000
    macros=np.array([q['bbox_dbu'] for q in m['macros']],float).reshape(-1,4)/2000
    bg=legacy.background(c,dims);eligible=[i for i,r in a.iterrows() if r.pin in anchor and bool(cc.loc[i,'moved'])]
    ids=eligible[::max(1,len(eligible)//64)][:64]
    plt=legacy.plt;fig,axes=plt.subplots(1,2,figsize=(13,8.5));fig.subplots_adjust(left=.065,right=.97,bottom=.22,top=.79,wspace=.18)
    fig.text(.06,.94,TITLES[c]+' | 真实端点依据与几何连线示意',fontsize=21,weight='bold')
    fig.text(.06,.89,f'全表端点来自冻结 ODB；图中抽样 {len(ids)} 个有端点 pin，完整逐 pin 数量/坐标见 CSV。',fontsize=10,color='#56677d')
    for ax,frame,label in zip(axes,[a,cc],['A. 原始位置','C. proposed 内部二维']):
        legacy.draw_base(ax,bg,dims,macros)
        for i in ids:
            r=frame.loc[i];xy=r[['x_um','y_um']].to_numpy(float);points=anchor[r.pin]
            end=points[np.argmin(abs(points-xy).sum(axis=1))]
            ax.plot([xy[0],end[0]],[xy[1],end[1]],ls='--',lw=.65,color=legacy.COLORS[r.interface],alpha=.55,zorder=3)
            ax.plot(*end,marker='x',ms=3,color='#17283c',zorder=5)
        legacy.points(ax,a,frame[['x_um','y_um']].to_numpy(float));ax.set_title(label,loc='left',weight='bold')
    fig.text(.06,.08,'× = 经 BUF/INV 追踪至的真实内部 ITerm bbox 中心（最多12级，存储/逻辑实例保持）；\n虚线仅表示直线几何关系，既非数据库布线路径，也非新接入方案；同一 pin 的最近端点可能随位置改变。\n圆/方为显示标记，不表示 pin、通孔的实际尺寸。浅色底图不能证明上方金属可用。',fontsize=10,color='#56677d')
    for ext in ['png','svg']:fig.savefig(root/f'{c}_endpoints.{ext}',dpi=180)
    plt.close(fig)

def hierarchy(out):
    plt=expand.legacy.plt;R=expand.legacy.Rectangle
    fig,axes=plt.subplots(1,2,figsize=(16,7));fig.subplots_adjust(left=.025,right=.98,top=.84,bottom=.16,wspace=.12)
    fig.text(.03,.94,'完整功能归属与物理粒度 | SYSTEM 包装复用 Issue55',fontsize=22,weight='bold')
    content=[('openTPU / otpu_asic_top',[('ACT','Activation SRAM\nscale / ACT 地址'),('MXU','矩阵 / FIFO\nFP 后处理'),('SYSTEM','VPU · TMEM · sequencer/IMEM\nquant · DMA · collective\n仲裁 / mux / 状态 / glue')]),
             ('llaccel / llaccel_core',[('GEMM','矩阵 / 累加 / epilogue\n输出 FIFO / 请求状态'),('VECTOR','向量 / walker / splitter\nreduction / division / 队列'),('SYSTEM','ATTENTION · cmd_proc · DMA\nSRAM xbar · DRAM arb · perf\n顶层连接 / 状态 / glue')])]
    for ax,(title,boxes) in zip(axes,content):
        ax.set_xlim(0,10);ax.set_ylim(0,6);ax.axis('off');ax.set_title(title,loc='left',fontsize=16,weight='bold')
        ax.add_patch(R((.1,.3),9.7,5.4,fill=False,ec='#52667d',lw=1.5))
        for (name,desc),x,y,w,h,color in zip(boxes,[.5,5.2,.5],[3.7,3.7,.7],[4,4,8.7],[1.5,1.5,2.4],['#d9eaf4','#d6eee4','#eee5f5']):
            ax.add_patch(R((x,y),w,h,fc=color,ec='#52667d',lw=1));ax.text(x+.2,y+h-.35,name,weight='bold',fontsize=14)
            ax.text(x+.2,y+.25,desc,fontsize=11,va='bottom')
        for x in [2.5,7.1]:ax.annotate('',(x,3.65),(x,3.15),arrowprops={'arrowstyle':'<->','color':'#52667d'})
        ax.text(.45,.37,'TOP_IO：外部端口和时钟源；父层只保留三块之间的连线',fontsize=9)
    fig.text(.03,.035,'系统按3个物理叶块计数；SYSTEM 内功能子层次完整归属，不额外重复计硬宏。ACT+MXU 是替代粒度。\n外部 DRAM、host/封装不在设计内；llaccel_core 的16个外部 SRAM bank 存储本体未计入已实现 block。',fontsize=11,color='#56677d')
    for ext in ['png','svg']:fig.savefig(out/f'hierarchy.{ext}',dpi=180)
    plt.close(fig)

def build(root,out,keep_figures=False):
    root=Path(root).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    assets=out/'assets';data=out/'data';assets.mkdir(exist_ok=True);data.mkdir(exist_ok=True)
    if not keep_figures or not (assets/'hierarchy.png').exists():hierarchy(assets)
    for c in ORDER:
        if c not in ['act','gemm']:
            if not keep_figures or not (root/f'{c}_endpoints.png').exists():endpoint_plot(root,c)
            for kind in ['comparison','zoom','endpoints']:
                for ext in ['png','svg']:shutil.copy2(root/f'{c}_{kind}.{ext}',assets)
        compress(root/f'{c}_pin_coordinates.csv',data/f'{c}_pin_coordinates.csv.gz')
        compress(root/f'{c}_groups.csv',data/f'{c}_groups.csv.gz')
        for suffix in ['_metrics.json','.meta.json','_validation.json','_patches.json']:
            p=root/(c+suffix)
            if p.exists():shutil.copy2(p,data)
    for p in (root/'inventory').iterdir():
        if p.suffix=='.csv':compress(p,data/(p.name+'.gz'))
        elif p.suffix=='.json':compress(p,data/(p.name+'.gz'))
    evidence=data/'evidence';evidence.mkdir(exist_ok=True)
    for c in ['mxu','vector','opentpu_aux','llaccel_aux']:
        dest=evidence/c;dest.mkdir(exist_ok=True)
        for name in ['receipt.json','anchors.tsv.gz','endpoints.tsv.gz','bterms.tsv.gz','tech.tsv.gz','vias.tsv.gz','macros.tsv.gz','design.tsv.gz']:
            p=root/'physical'/c/name
            if p.exists():shutil.copy2(p,dest/name)
    notes=root.parent/'source_notes/issue55/runs'
    for d in notes.iterdir():
        if d.is_dir():
            dest=evidence/d.name;dest.mkdir(exist_ok=True)
            for p in d.iterdir():
                if p.is_file() and p.suffix=='.json':compress(p,dest/(p.name+'.gz'))
    physical_evidence=root/'trial_receipts'
    if physical_evidence.exists():
        latest=sorted(p for p in physical_evidence.iterdir() if p.is_dir())[-1]
        published=evidence/'physical';published.mkdir(exist_ok=True)
        for prior in published.iterdir():
            if prior.is_dir():
                assert published.resolve() in prior.resolve().parents
                shutil.rmtree(prior)  # only duplicated generated publication copies; originals retained
        shutil.copytree(latest,published/latest.name,ignore=shutil.ignore_patterns('timing.selected_*.txt.gz'))
        # Tool text is losslessly compressed; preserve exact report bytes and
        # avoid whitespace normalization of evidence during Git publication.
        for p in published.rglob('*'):
            if p.is_file() and p.suffix in ['.drc','.txt','.tsv']:
                compress(p,p.with_name(p.name+'.gz'))
                assert published.resolve() in p.resolve().parents
                p.unlink()
    shutil.copy2(root/'coverage_gate.json',data)
    shutil.copytree(root/'pin-use-r01',data/'pin-use-r01',dirs_exist_ok=True)
    shutil.copy2(root/'pin_use_correction.json',data)
    for c in ['mxu','vector','opentpu_aux','llaccel_aux']:
        prior=data/'candidate_revision_r01'/c;prior.mkdir(parents=True,exist_ok=True)
        compress(root/'revisions/r01'/c/f'{c}_pin_coordinates.csv',prior/f'{c}_pin_coordinates.csv.gz')
        shutil.copy2(root/'revisions/r01'/c/f'{c}_metrics.json',prior)
        shutil.copy2(root/f'{c}_grid_revision.json',data)
    shutil.copytree(root/'native_grid',data/'native_grid',dirs_exist_ok=True)
    # Preserve exact compact hierarchy/frontier and origin proof for reproducing ownership.
    for p in (root/'partition-r02').iterdir():
        if p.is_file():
            if p.suffix=='.gz':shutil.copy2(p,data)
            else:compress(p,data/(p.name+'.gz'))
    cfg=json.loads((HERE/'sources.json').read_text());dump(data/'sources.json',cfg)
    from plot_actual_access import draw
    draw(root,out)
    summary=json.loads((root/'inventory/partition_summary.json').read_text());bindings=json.loads((root/'inventory/binding_summary.json').read_text())
    physical=root/'physical_summary.json';pstat=json.loads(physical.read_text(encoding='utf-8')) if physical.exists() else {}
    dump(data/'physical_summary.json',pstat)
    measured=pstat.get('act',{}).get('matched_740pin_comparison',{})
    measured_rows=[{'试验':k,'同组pin':v['selected_pins'],'DRT实际总线长 μm':v['wire_length_um'],'DRT via数量':v['via_count'],'线长变化':f"{v['wire_change_percent']:+.2f}%",'via变化':f"{v['via_change_percent']:+.2f}%",'setup余量 ns':v['setup_worst_slack_ns'],'hold余量 ns':v['hold_worst_slack_ns']} for k,v in measured.get('plans',{}).items()]
    measured_html=('<h3>ACT同组740-pin实际对照</h3>'+table(pd.DataFrame(measured_rows))+'<p>这是DRT在RCX前输出的真实路由统计，按工具口径计数，区别于几何L1及RC/STA。单次匹配试验中C线长约−6.40%、via约−1.70%，远小于几何L1的−42.4%；setup余量略变差，没有时序改善结论。B仅为相同740-pin子集。A原边界已能合法布线；C提供内部线长的额外价值，父层代价/通道和完整规则仍未知，外框未缩小。</p>') if measured_rows else ''
    metrics={c:json.loads((root/f'{c}_metrics.json').read_text()) for c in ORDER}
    totals=[];htmlparts=[];pins=[]
    for c in ORDER:
        m=metrics[c];source='../issue-119-pin-xy/assets' if c in ['act','gemm'] else 'assets'
        totals.append({'block':TITLES[c],'信号pin':m['A']['n'],'M5':m['A']['layers']['metal5'],'M6':m['A']['layers']['metal6'],'B移动':m['B']['moved'],'C移动':m['C']['moved'],'来源':'PR120 原样复用' if c in ['act','gemm'] else '本任务新增'})
        rows=[]
        for p in ['A','B','C']:
            q=m[p];base=m['A']['nearest_traced_L1_sum_um'];change=100*(q['nearest_traced_L1_sum_um']/base-1)
            rows.append({'方案':p,'移动':q['moved'],'保留':q['fixed'],'几何端点L1变化':f'{change:+.1f}%','异网同层相交pin':q['pin_overlap'],'基础间距风险pin':q['pin_spacing'],'PG相交pin':q['pin_pg_overlap'],'M5最小NN μm':round(q['min_nn_per_layer_um']['metal5'],4),'M6最小NN μm':round(q['min_nn_per_layer_um']['metal6'],4),'20μm窗最大pin':q['max_pin_count_20um_square_sampled'],'候选窗口面积和 μm²':round(q['sum_nonoverlap_patch_envelopes_um2'],2)})
        htmlparts.append(f'<article id="{c}"><h2>{TITLES[c]}</h2><p>{RECOMMEND[c]}</p><img loading="lazy" src="{source}/{c}_comparison.png" alt="{c}全pin对照"><div class="scroll">{table(pd.DataFrame(rows))}</div><p>区域面积为候选组窗口包络和，不是通孔占地、可用金属面积或节省面积。密度是采样20μm窗口统计，最小NN是点中心几何距离；按层实际尺寸/规则判断风险。</p><details open><summary>密集区实际金属放大</summary><img loading="lazy" src="{source}/{c}_zoom.png"></details><details><summary>真实内部端点与示意连线</summary><img loading="lazy" src="{source}/{c}_endpoints.png"></details><p><a href="{source}/{c}_comparison.svg">SVG对照</a> · <a href="data/{c}_pin_coordinates.csv.gz">全部逐pin A/B/C CSV.gz</a> · <a href="data/{c}_groups.csv.gz">分束对应</a> · <a href="data/{c}_metrics.json">完整几何指标</a></p></article>')
        d=pd.read_csv(root/f'{c}_pin_coordinates.csv',low_memory=False)
        frames={p:d[d.plan==p].set_index('pin') for p in ['A','B','C']}
        for name,r in frames['A'].iterrows():
            b=frames['B'].loc[name];cc=frames['C'].loc[name]
            pins.append([c,name,r.bus,r.interface,r.direction,r.layer,*[round(float(x),6) for x in [r.x_um,r.y_um,b.x_um,b.y_um,cc.x_um,cc.y_um]],str(cc.get('retention_or_movement_reason','PR120 原有分束/保留依据，见原报告'))])
    own=pd.read_csv(root/'inventory/functional_ownership.csv');matrix=pd.read_csv(root/'inventory/connection_matrix.csv')
    stages=[]
    for c in ORDER:
        p=pstat.get(c,{})
        stages.append({'block':TITLES[c],'划分/接口':'完成；物理port逐bit匹配','候选/几何':'全pin A/B/C覆盖','实际接入':p.get('route_status','未执行/尚未收集'),'DRC/连通':p.get('drc_status','候选不代表通过'),'RC/STA/电气':p.get('sta_status','尚未收集'),'父层接入':'原始handoff/实际层序未知'})
    rawpins=json.dumps(pins,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    report='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>全功能分块与二维pin布局研究 · Issue126</title>
<style>body{font:16px/1.75 "Microsoft YaHei",sans-serif;color:#17283c;background:#f1f4f8;margin:0}main{max-width:1560px;margin:auto;padding:32px}h1{font-size:32px}h2{border-bottom:2px solid #d9e3ed;padding-bottom:12px}article,.card{background:white;border:1px solid #dce4ed;border-radius:12px;padding:24px;margin:24px 0}.warn{background:#fff3df;border-left:5px solid #c8892b;padding:18px}img{max-width:100%;height:auto}.scroll{overflow:auto}table{border-collapse:collapse;font-size:13px;width:100%}th,td{border:1px solid #dce4ed;padding:8px;text-align:left}th{background:#edf3f8}a{color:#0072b2}code{overflow-wrap:anywhere}input,select{font:inherit;padding:8px;margin:4px}small{color:#56677d}details{margin:18px 0}nav a{margin-right:18px}footer{font-size:13px;color:#56677d}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:600px;overflow:auto;font-size:12px}</style>
<main><h1>openTPU / llaccel 完整功能分块与二维 pin 研究</h1><p>Issue126 · Nangate45 · 2026-10-27 · PR120 增量扩展。固定功能与连接语义，保留原 M5/M6 pin 层、矩形尺寸、外框和允许布线层集合。M1–M10 是固定底座研究背景；本轮不增加 M11/M12，也不重指派目标层。</p>
<div class="warn"><b>阶段边界：</b>全六块候选覆盖已完成，24,767个原始信号pin，74,301行 A/B/C 坐标。候选、局部接入试验与完整物理资格分开记录；不宣称已完成全C重硬化、父层接入、完整DRC/RC/STA，也不从几何L1推断时序或面积节省。</div>
<nav><a href="#partition">完整划分</a><a href="#coverage">覆盖</a><a href="#physical">实际物理阶段</a><a href="#query">逐pin查询</a>__NAV__</nav>
<section class="card" id="partition"><h2>完整功能归属，三块/系统的明确物理粒度</h2><p>复用 Issue55 已有真实 SYSTEM 包装、冻结 RTL、层次与结构连通证明；本任务没有另造协议、流水或缓存。ACT/MXU/SYSTEM 与 GEMM/VECTOR/SYSTEM 各自构成完整父层接口。SYSTEM 是合法粗粒度物理叶块，内部功能不漏项，不要求每个辅助 RTL 单独硬化。</p><img src="assets/hierarchy.png"><div class="scroll">__OWN__</div>
<p>ACT+MXU 合并版仅为替代粒度，未与 ACT/MXU 重复统计。openTPU VPU 和 llaccel VECTOR 不是同一模块。llaccel 顶层固定为 llaccel_core；llaccel_top 的16个外部 SRAM bank 存储本体不包含在该物理系统内。外部DRAM、host、封装及外设不虚构为已实现block。</p>
<p>顶层基础设施保留外部端口和时钟源入口，以及三块间纯连接；所有计算、存储、控制、搬运、仲裁、状态和胶合逻辑均归属上述叶块。冻结层次展开：openTPU 32,617个叶单元，llaccel 27,484个，未归属叶单元均为0；含状态/记忆单元分别3,015/722。此为RTL/综合前图数量，不能当作物理标准单元数量。</p>
<p>配置与来源：openTPU原始f237dab2，D32/MCOLS2/ACT_BLOCKS32/ACT_ROWS2/TMEM_WORDS16384/IMEM_WORDS8192；llaccel原始f7db8a22，EPILOGUE_FUSION0/DMA_MAX_OUTSTANDING16。实际冻结输入还含Issue55包装与变换，精确哈希见 input_manifest、partition_summary 与 source index，不能仅靠上游commit复现。部分原层次参数导出缺失，保留源码/-G/默认值证据，不伪称从JSON观察到。</p>
<p>继承结构证明：两个系统的原始平坦叶图/连接/状态与包装后图逐项比较；openTPU另有20例有限配对回放通过。有限回放不是完整形式等价，物理网表和完整功能时序仍单独验收。</p>
<h3>逻辑连接矩阵</h3><div class="scroll">__MATRIX__</div><p>计数为展开后的逐bit驱动-接收端关系，可能含同一信号扇出，不能相加当独立网络或pin数。数字net ID仅在相应模块域内解释；常量按值记录，不把所有0字面量并作真实共同网络。</p>
<p><a href="data/interfaces.csv.gz">完整接口组/方向/位宽</a> · <a href="data/connections.csv.gz">逐bit逻辑连接</a> · <a href="data/connections_physical_endpoints.csv.gz">连接两端原pin层</a> · <a href="data/pin_bindings.csv.gz">24,767条物理pin与逻辑接口绑定</a> · <a href="data/partition_summary.json.gz">配置/层次摘要</a></p></section>
<section class="card" id="coverage"><h2>全部信号pin覆盖与几何方案</h2><div class="scroll">__TOTAL__</div><p>原始布局A使用真实数据库坐标。ACT/GEMM候选逐字节复用PR120（head4f91e098），未重新生成以掩盖已知冲突。新四块按真实ODB边界、ITerm/BUF/INV追踪端点、宏、路由金属、通孔、PG和实际OBS筛查。</p>
<p>B：原边附近1.12μm中心距的多排/错位；C：2.24μm中心距、8.96μm候选中心网格、距边界至少max(15.68μm,2%块边长)的真实内部窗口。矩形宏外扩0.56μm只是候选保护假设，不是工艺via keepout。窗口允许按端点聚簇，不均匀铺满。时钟/复位、未能追踪端点、无证据适合内移的窄控制、恒零整字节等按CSV理由保留。</p>
<p>已验证束语义：MXU的4路32-bit t_wdata/t_wen lane；GEMM/VECTOR写数据与byte strobe、高半常量位；llaccel SYSTEM的bank_wdata/bank_we按字节保持关联。其余“每32bit”是绘图/候选分段假设，不能视为真实bank或lane。实际逻辑bus/事务映射见groups与pin_bindings。</p>
<p>几何筛查包括逐层原pin矩形异网相交、基础间距、PG、OBS、宏bbox和候选间距；未在这个阶段验证实际新接入的轨道、via cut/enclosure、完整LEF58规则或父层可访问性。M6/M8/M10通孔堆叠仅作明确假设的敏感性比较，尺寸与间距来自各块导出的tech/vias，不统一套用最高层间距；两个SYSTEM允许顶层为M8，M10敏感性列明确非法且不用于方案资格。</p>
<p>父层逐pin逻辑连接已补齐，对端原始M5/M6层可以核对；原始父层真实handoff层、实际穿层序列仍全部未知，不能把对端M5/M6等同于父层M8接入。连接语义没有改变，未知目标保持未知，后续需要版本匹配的父层数据库。</p></section>
__BLOCKS__
<section class="card" id="physical"><h2>独立物理验证阶段</h2><div class="scroll">__STAGES__</div><p>小区域对照固定同一8个pin，其余pin保持原始位置；A读取原始边界，Aopt只在相同边/相同层的原有8个边界槽位内做分配优化，B/C采用相应候选坐标。Aopt使用C中心作端点导向代理成本，不能称为全局最优边界。place_pin真实写入ODB并核对中心和原层/尺寸；只清除相关网络原dbWire，然后实际global_route/detail_route。保留原单元与宏位置、规格、CTS和PDN，不删OBS、不修驱动掩盖XY成本。</p><p>A_replay保持原XY但重新接同一组网络，区分重跑布线本身影响。后续ACT完整740-pin C的独立对照另用fullC-r01记录，B只取同一740-pin cohort，不能冒充完整859-pin B；其实际阶段以回执为准。</p><img loading="lazy" src="assets/act_actual_access.png"><p><a href="assets/act_actual_access.svg">实际接入SVG</a> · <a href="data/act_actual_access_via_geometry.csv">实际via cut层尺寸/数量</a>；尺寸来自实际路由数据库，不是最大层通用间距假设。</p>
<div class="warn"><b>实际发现并隔离的工具问题：</b>当前OpenRCX提取后保存的ODB重新读入，会产生大量native DRC冲突；ACT逐阶段试验确认读写/加载/约束前DRC=0，extract后ODB重读报12534项。旧checked.odb不作为物理母本。使用提取前routed.odb（A用原始ODB）在新进程导出clean.odb、视图并独立DRC/全块连通；clean与提取前输入逐字节一致。SPEF/STA保留其同一提取前来源，并明确系统边界不完整。全部旧失败和分析状态诊断保留，未降低规则。</div><p>新增四块另按实际0.005μm制造网格修订候选r02，最大轴向修正均小于0.0025μm；保留原r01逐pin坐标/指标及被place_pin对齐的失败。此为已在内部的二维候选之网格修正，不是把边缘微移伪装成内部二维。实际试验采用原相同8pin cohort重试，层/方向/连接语义不变。</p><p>DRT完成、独立clean进程native DRC、全块几何连通、PDN、OpenRCX、setup/hold/电气检查分别记录；命令执行成功不等于各规则通过。继承baseline未通过项继续保留。精确阶段、失败与工具输出见<a href="data/physical_summary.json">物理回执</a>；原始大型ODB/DEF/SPEF留在授权独立远程目录，输出SHA索引见execution.json。</p><pre>__PHYSICAL__</pre>
<p>物理底座使用原Nangate45平台：signal M2–M10/clock M4–M10；两个SYSTEM保持其原上限M8。没有M11/M12扩展。OpenROAD显示版本unknown，采用可执行文件SHA0a4cdf08…锁定；原研究宏Liberty不是生产SRAM时序签核库。块外框未缩小，不报告block面积节省；没有真实缩小通道/总体边界也不报告系统面积收益。</p></section>
<section class="card" id="query"><h2>逐pin查询（完整数据，显示上限100行）</h2><select id="case"><option value="">全部block</option>__OPTIONS__</select><input id="search" placeholder="pin / bus / 类别 / 保留理由"><p id="count"></p><div class="scroll"><table><thead><tr><th>block</th><th>pin</th><th>bus</th><th>类别</th><th>方向</th><th>层</th><th>A XY μm</th><th>B XY μm</th><th>C XY μm</th><th>C依据</th></tr></thead><tbody id="rows"></tbody></table></div></section>
<section class="card"><h2>来源、可复现入口和限制</h2><p><a href="https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/120">PR120</a>未合并成果为起点；<a href="https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/58">Issue55/PR58</a>提供已存在的完整包装/结构证明和两个已完成SYSTEM路由源。没有接管其活动作业，也没有把其待验证项改成通过。</p><p><a href="data/sources.json">六块实际数据库路径/SHA</a> · <a href="data/coverage_gate.json">覆盖回执</a> · <a href="data/artifact_index.json">交付文件SHA索引</a> · <a href="../../../project/experiments/full_pin_xy/README.md">脚本与命令</a></p><p>原参考HTML及ref-project、历史实验、PR120旧工作树均保持完整。新结果只写issue126独立目录。几何端点L1不是真实布线线长；实际线长由数据库路由段统计，RC由OpenRCX提取；两者与STA结果单独比较。候选图不能代表合法实现图。</p></section><footer>本报告保留负结果与未知条件。每块推荐取决于本次固定配置、原目标层证据和密度；不泛化为所有大模型或所有划分粒度。</footer></main>
<script>const pins=__PINS__;const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));function render(){const c=document.querySelector('#case').value,q=document.querySelector('#search').value.toLowerCase();let a=pins.filter(r=>(!c||r[0]===c)&&r.join(' ').toLowerCase().includes(q));document.querySelector('#count').textContent=`匹配 ${a.length} / ${pins.length} 原始信号pin；所有方案保持同一完整清单。`;document.querySelector('#rows').innerHTML=a.slice(0,100).map(r=>'<tr>'+[...r.slice(0,6),r[6]+', '+r[7],r[8]+', '+r[9],r[10]+', '+r[11],r[12]].map(s=>'<td>'+escape(s)+'</td>').join('')+'</tr>').join('')}document.querySelectorAll('input,select').forEach(e=>e.addEventListener('input',render));render();</script></html>'''
    replacements={'NAV':''.join(f'<a href="#{c}">{TITLES[c]}</a>' for c in ORDER),'OWN':table(own),'MATRIX':table(matrix),'TOTAL':table(pd.DataFrame(totals)),'BLOCKS':'\n'.join(htmlparts),'STAGES':table(pd.DataFrame(stages)),'PHYSICAL':html.escape(json.dumps(pstat,ensure_ascii=False,indent=2)),'OPTIONS':''.join(f'<option>{c}</option>' for c in ORDER),'PINS':rawpins}
    for k,v in replacements.items():report=report.replace('__'+k+'__',v)
    report=report.replace('<pre>'+html.escape(json.dumps(pstat,ensure_ascii=False,indent=2))+'</pre>',measured_html+'<pre>'+html.escape(json.dumps(pstat,ensure_ascii=False,indent=2))+'</pre>')
    (out/'report.html').write_text(report,encoding='utf-8')
    for p in out.rglob('*'):
        if p.is_file() and p.suffix in ['.svg','.html','.json','.csv']:
            # Normalize only text representation of generated/publication data.
            # Native tool text is preserved byte-exact in gzip above.
            s=p.read_text(encoding='utf-8');p.write_text('\n'.join(line.rstrip() for line in s.splitlines())+'\n',encoding='utf-8',newline='\n')
    dump(data/'artifact_index.json',{str(p.relative_to(out)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(out.rglob('*')) if p.is_file() and p.name!='artifact_index.json'})
    print('REPORT_COMPLETE',out,'original_pins',len(pins),'rows',3*len(pins))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',required=True);p.add_argument('--keep-figures',action='store_true');a=p.parse_args();build(a.root,a.out,a.keep_figures)
