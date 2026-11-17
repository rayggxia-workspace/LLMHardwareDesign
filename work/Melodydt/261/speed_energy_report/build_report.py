from pathlib import Path
import json, math, shutil, hashlib, sys
from xml.sax.saxutils import escape
from collections import Counter
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Flowable, Image
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader
from root_data import build

BASE=Path(__file__).resolve().parent
REPO=BASE.parents[3]
SHARED=Path(r'C:\Users\Administrator\.codex\visualizations\2026\11\12\01a1cf68-c2d6-71e2-9ffe-213316929684')
OUT=REPO/'output'/'pdf'
OUT.mkdir(parents=True,exist_ok=True)
SOURCES=BASE/'sources';SOURCES.mkdir(exist_ok=True)
for n in ['edgecim','chime','fpga','asic_pim']:
    if not (SOURCES/f'research_{n}.json').exists():
        shutil.copy2(SHARED/f'research_{n}.json',SOURCES/f'research_{n}.json')
def read(n): return json.loads((SOURCES/f'research_{n}.json').read_text(encoding='utf-8-sig'))
papers=build(); byid={p['id']:p for p in papers}
def add(p):papers.append(p);byid[p['id']]=p;return p
def nz(v):return '未明' if v is None else str(v)
edge=read('edgecim')['rows']
for id,rs,title,kind,notes in [
 ('E01',edge[:24],'EdgeCIM: A Hardware-Software Co-Design for CIM-Based Acceleration of Small Language Models','SRAM-CIM',
  'B1，128输入/128输出；逐模型和位宽独立搜索配置。速度与能效均取v1同一图，避免与v2图例混用。INT4/INT8沿用作者标签，激活位宽未核实。全部为近似图读数。'),
 ('G01',edge[24:],'Jetson GPU 实测参考（来自 EdgeCIM v2）','GPU 实测参考',
  'B1，128输入/128输出，MAXN；MLC LLM 0.1.3，TVM0.18.1，CUDA12.6。预热1轮、4轮平均；tegraStats每100ms采样，减运行前5s空闲均值。属于动态模块能效，不能当墙插总能效。')]:
    rr=[]
    for r in rs:
        rr.append(dict(model=r['model'],precision=r['precision'],stage='decode',tps=r['tps'],tpj=r['tpj'],power=None,
          conditions=('INT4/INT8独立搜索；128/128' if id=='E01' else r['work'].split(' (')[0]),method='图估读',source=r['source']))
    add(dict(id=id,title=title,kind=kind,url=rs[0]['source'],locator=rs[0]['locator'],hardware=(rs[0]['process']+'；'+rs[0]['memory']),boundary=rs[0]['boundary'],notes=notes,rows=rr))
ch=read('chime')
add(dict(id='E02',title='CHIME: Chiplet-based Heterogeneous Near-Memory Acceleration for Edge Multimodal LLM Inference',kind='DRAM/RRAM NMP',url=ch['rows'][0]['source'],locator='arXiv:2601.19908v1；表 II-V、图 6-7',
 hardware='40 nm逻辑综合缩放7 nm；1 GHz；35 nm DRAM 200层+28 nm CNFET RRAM 8层。两块逻辑die 28.71/24.85 mm²。',
 boundary='作者总体报233-533 tokens/s及116.5-266.5 tokens/J；仅对该区间取倒数为约0.00375-0.00858 J/token，不能分配到各模型。表V的2 W、图6约1.3-1.7 W及图7分项约6.8 W不一致，逐模型能效不推算。',
 notes='FP16；512×512图像+128文本token，输出488；batch未明。吞吐未明确分离prefill/decode，图估读仅列两位有效数。',
 rows=[dict(model=r['model'],precision='FP16',stage='MLLM生成',tps=r['tps'],tpj=None,power=None,conditions='图像+128文本；488输出',method='图估读') for r in ch['rows']]))

for p in read('fpga')['papers']:
    rr=[]
    for r in p['metrics']:
        tpj=r.get('tokens_j_reported')
        calc=tpj is None and r.get('tokens_j_calculated') is not None
        if tpj is None:tpj=r.get('tokens_j_calculated')
        cond=[r.get('config',''),f"B={nz(r.get('batch'))}"]
        if r.get('input_tokens') is not None:cond.append(f"{r['input_tokens']}/{r['output_tokens']}")
        rr.append(dict(model=r['model'].split('（')[0],precision='',stage=r['stage'],tps=r['tokens_s'],tpj=tpj,power=r.get('power_w'),conditions='；'.join(x for x in cond if x),method='换算' if calc else '原文',source=r['source']))
    add(dict(id=p['id'],title=p['title'],kind=p['type'],url=p['url'],locator=p['version']+'；'+p['source_locations'],hardware=p['platform']+'；'+p['memory'],
      area=p['area'],boundary=p['power_scope'],notes=p['precision']+' '+p['test_conditions'],evaluation=p['evaluation'],caveats=p['caveats'],rows=rr))

cnmeta={
 'LEAP':('RRAM PIM + NoC','45 nm数字逻辑综合/P&R缩放7 nm；1 GHz；每宏128×128交叉阵列、32 KB SRAM+256 B路由缓冲；0.1181 mm²/宏，非系统面积。',
   '模型包含PIM PE、scratchpad及路由功耗；不代表主机/墙插实测。10.53 W为表III共同系统值。',
   '1024输入/1024输出；8-bit存储单元+16-bit数据通路，不能直接标W8A8。表内端到端吞吐分子是否含输入token未明；8B/13B系统规模未单列。'),
 'CENT':('CXL GDDR6-PIM','1Y nm GDDR6-PIM、1 GHz；CXL控制器28 nm综合缩放7 nm，19 mm²/控制器。32设备配置512 GB；512 TB/s为内部PIM带宽。',
   '模型含DRAM背景/命令、PIM、控制器、向量/RISC-V和通信；主机采样能耗未明。能效按作者1000/[mJ/token]，不能用所列TPS÷W重算。',
   'BF16；512输入/3584输出。作者对采样长度的TPS、能量及功率分别平均，功率用PIM时延而TPS含CXL等开销。端到端分子计输入+输出4096；70B为32设备配置中27活跃。'),
 'Coffee':('多加速器数字 ASIC','ASAP7预测7 nm、1 GHz；288加速器系统，每加速器16×2048计算核；聚合 HBM 带宽 32 TB/s；总面积未报告。',
   '综合与VCD+系统模型；包含逻辑、SRAM、HBM(3.5 pJ/bit)、静态和通信。表中W由TPS/能效反算，仅用于说明规模。',
   '平均4-bit预算，INT2-5混合；FP16 prefill。PG-19工作量，每组采用内存可容纳的最大batch；K按原文保留。模型/长度/batch不同，不按总吞吐比较单用户体验。'),
 'HNLPU':('固定权重 ASIC','5 nm；1 GHz；827.08 mm²/芯片；16芯片共约13232 mm²；HBM PHY及CXL3.0 4×4互联。',
   '布局后/周期仿真及PrimeTime PX、CNSim；6.9 kW为论文系统功耗，不用16×308.39 W芯片功耗替代。',
   '硬连线FP4 gpt-oss120B权重；2K长度；实际batch及输入输出拆分未明，216只是最大支持batch。原报36226 tokens/kJ除1000得到36.226 tokens/J。'),
 'DynaTE':('扩散语言模型 ASIC','TSMC28 nm；1 GHz；3.91 mm²=逻辑2.12+SRAM1.79；主要缓冲576 KB；HBM2 512 GB/s。',
   'RTL综合+CACTI7+Ramulator周期模型；7.36 W=逻辑1.01+SRAM1.18+片外HBM5.17。',
   'W8A8/W8A4动态激活精度；输出256。24.89 tokens/s与3.38 tokens/J是LLaDA8B、Dream7B在五任务上的平均，不是任一模型独立值；输入和batch未明。')}
asic=read('asic_pim')
for i,p in enumerate(asic['works'],1):
    id=f'A{i:02d}';kind,hw,bound,notes=cnmeta[p['id']]
    rr=[]
    for r in p['rows']:
        cond=[]
        if r.get('devices'):cond.append(f"{r['devices']}设备")
        cond.append(f"B={nz(r.get('batch'))}")
        it=r.get('input_tokens_label',r.get('input_tokens',p.get('input_tokens')));ot=r.get('output_tokens_label',r.get('output_tokens',p.get('output_tokens')))
        if it is not None or ot is not None:cond.append(f'{nz(it)}/{nz(ot)}')
        phase={'paper-reported end-to-end':'端到端*','decoding':'decode','end2end':'端到端*','system inference, prefill/decode split unspecified':'系统推理*','end-to-end diffusion generation':'扩散生成平均'}.get(r['phase'],r['phase'])
        model=r['model']
        if p['id']=='DynaTE':model='LLaDA-8B + Dream-7B平均'
        rr.append(dict(model=model,precision='',stage=phase,tps=r['tokens_per_second'],tpj=r['tokens_per_joule'],power=r.get('power_w'),conditions='；'.join(cond),method='换算' if p['id'] in ['CENT','HNLPU'] else '原文',energy_per_token_mj=r.get('energy_per_token_mj')))
    add(dict(id=id,title=p['title'],kind=kind,url=p['paper_url'],locator=p['publication']+'；'+p['evidence_locator'],hardware=hw,boundary=bound,notes=notes,rows=rr))

# Six measured GPU rows from Coffee Table 3; preserve maximum feasible batch per row.
rr=[]
for model,values in [('Llama-3.1-8B',[(92167,30.57,4096),(3913,1.01,147),(4553,1.17,179)]),('Llama-3.1-70B',[(34136,9.03,3919),(1164,.34,52),(1679,.44,63)])]:
    for (t,e,b),io in zip(values,['1.4K/0.2K','114K/5K','90K/8K']):
        rr.append(dict(model=model,precision='NVFP4',stage='decode',tps=t,tpj=e,power=None,conditions=f'4×B200；B={b}；{io}',method='原文'))
add(dict(id='G02',title='4×B200 GPU 实测参考（来自 Coffee / Elastic Precision）',kind='GPU 实测参考',url='https://arxiv.org/html/2611.00915#S6',locator='2026 arXiv v1；表3、§6.1(c)',hardware='4×B200；聚合 HBM 带宽 32 TB/s；四路张量并行；vLLM0.31.0；关闭prefix caching。芯片面积/制程不用于本表。',
 boundary='NVML板卡能量；减去匹配的单token运行以分离decode开销，非整机墙插能量。功耗不从TDP换算。',
 notes='最大可容纳batch；NVFP4推理与KV缓存。保留PG-19工作量和K长度标签。此处是同一论文里的实测GPU参照，不能把论文的288加速器模型说成B200实测。',rows=rr))

for p in papers:
    for r in p['rows']:
        r['paper_id']=p['id'];r['paper_url']=p['url']
        r['j_per_token']=None if r['tpj'] is None else 1/r['tpj']
        r['j_per_token_derivation']='未报告' if r['tpj'] is None else '1 / 本记录未作显示舍入的tpj；继承原阶段、能量边界、图估读/条件换算和聚合口径'
allrows=[r for p in papers for r in p['rows']]
data=dict(title='大模型推理速度与能效综述',date='2026-11-17',issue=261,base_commit='33c9743b8a50362501accb56bba08796e6e0f88d',
  units={'tps':'tokens/s, stage-specific','tpj':'tokens/J, energy-efficiency, higher is better','j_per_token':'J/token, reciprocal of stored tpj, lower is better','power':'W, scope-specific'},papers=papers,rows=allrows,
  caveat='文献数据摘录/换算，不是本项目新仿真；不同模型、阶段、批量和功耗边界不能混排。')
(OUT/'issue-261-llm-speed-energy-data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')

pdfmetrics.registerFont(TTFont('CJK',r'C:\Windows\Fonts\msyh.ttc',subfontIndex=0))
pdfmetrics.registerFont(TTFont('CJKB',r'C:\Windows\Fonts\msyhbd.ttc',subfontIndex=0))
pdfmetrics.registerFontFamily('CJK',normal='CJK',bold='CJKB')
PAGE=landscape(A4);W,H=PAGE;M=42;CW=W-2*M
NAVY=colors.HexColor('#17314C');TEAL=colors.HexColor('#007E87');INK=colors.HexColor('#213344');MUTED=colors.HexColor('#596C7D');PALE=colors.HexColor('#EFF5F8');ORANGE=colors.HexColor('#AD6116')
styles={
 'h1':ParagraphStyle('h1',fontName='CJKB',fontSize=21,leading=29,textColor=NAVY,spaceAfter=10,wordWrap='CJK'),
 'h2':ParagraphStyle('h2',fontName='CJKB',fontSize=13.5,leading=19,textColor=TEAL,spaceBefore=7,spaceAfter=6,wordWrap='CJK'),
 'body':ParagraphStyle('body',fontName='CJK',fontSize=10,leading=16,textColor=INK,spaceAfter=6,wordWrap='CJK'),
 'small':ParagraphStyle('small',fontName='CJK',fontSize=8.8,leading=13.3,textColor=MUTED,spaceAfter=4,wordWrap='CJK'),
 'cell':ParagraphStyle('cell',fontName='CJK',fontSize=8.8,leading=12.6,textColor=INK,wordWrap='CJK'),
 'head':ParagraphStyle('head',fontName='CJKB',fontSize=8.8,leading=12.8,textColor=colors.white,wordWrap='CJK'),
 'big':ParagraphStyle('big',fontName='CJKB',fontSize=34,leading=46,textColor=NAVY,spaceAfter=18,wordWrap='CJK'),
}
def clean(s):return str(s).replace('\u2011','-').replace('\u2013','-').replace('\u2014','-')
def P(s,style='body',raw=False):return Paragraph(clean(s) if raw else escape(clean(s)).replace('\n','<br/>'),styles[style])
def table(headers,rows,widths=None):
    d=[[P(x,'head') for x in headers]]+[[P(x,'cell') for x in row] for row in rows]
    t=Table(d,colWidths=widths or [CW/len(headers)]*len(headers),repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE]),('LINEBELOW',(0,0),(-1,0),.5,NAVY),('LINEBELOW',(0,-1),(-1,-1),.4,colors.HexColor('#BCD0DB'))]))
    return t
def fmt(v):
    if v is None:return '未报告'
    if isinstance(v,str):return v
    if abs(v)>=1000:return f'{v:,.0f}'
    if abs(v)>=100:return f'{v:.1f}'.rstrip('0').rstrip('.')
    if abs(v)>=1:return f'{v:.2f}'.rstrip('0').rstrip('.')
    return f'{v:.4f}'.rstrip('0').rstrip('.')

def jfmt(v):
    return '未报告' if v is None else '≈'+format(v,'.3g')

class Mark(Flowable):
    def __init__(self,k,label):super().__init__();self.k=k;self.label=label;self.width=0;self.height=0
    def draw(self):
        self.canv.bookmarkPage(self.k);self.canv.addOutlineEntry(self.label,self.k,level=0,closed=False);pages[self.k]=self.canv.getPageNumber()
def onpage(c,d):
    c.saveState();c.setStrokeColor(colors.HexColor('#D6E2E9'));c.line(M,H-29,W-M,H-29)
    c.setFillColor(MUTED);c.setFont('CJK',8);c.drawString(M,H-21,'LLM 推理速度与能效 | 文献证据汇总 · 2026-11-17')
    c.drawRightString(W-M,20,f'{d.page:02d}');c.drawString(M,20,'J/token 越低越省能量 · tokens/J 越高越省能量 · 保留阶段与能量边界')
    c.restoreState()

def metrics(p,rs=None):
    rows=[]
    for r in rs or p['rows']:
        approx='≈' if r['method']=='图估读' else ''
        cond=r.get('conditions','')
        if r['method']=='条件换算':cond+='；能效为条件换算'
        if p['id']=='A03':cond+='；W反算'
        precision=r.get('precision','') or {'A01':'8bit存储*','A02':'BF16','A03':'平均4bit','A04':'FP4','A05':'混合8/4bit'}.get(p['id'],'见说明')
        if p['id'] in ['R02','R03']:precision='三值/INT8'
        if p['id']=='G01':precision='W4A16'
        phase=r.get('stage','')
        phase=phase.replace('作者表列Throughput；严格分母/阶段边界未明','表列吞吐*').replace('输出tokens/E2E时间','端到端').replace('decoder层，总吞吐','decoder层/总吞吐')
        phase=phase.replace('peak decode','峰值解码').replace('扩散生成平均','扩散均值')
        model='LLaDA-8B / Dream-7B' if p['id']=='A05' else r['model']
        rows.append([model,precision,phase,approx+fmt(r['tps']),approx+fmt(r['tpj']) if r['tpj'] is not None else '未报告',jfmt(r['j_per_token']),fmt(r.get('power')),cond])
    return table(['模型','精度','阶段','tokens/s','tokens/J','J/token','功耗 W','测试条件 / 说明'],rows,[122,68,66,60,60,70,54,CW-500])
def details(p,rs=None,subtitle=None,compact=False,anchor=True):
    elems=[]
    short={'A02':'CENT','A03':'Coffee','A04':'HNLPU','G01':'Jetson GPU 实测参考','G02':'4×B200 GPU 实测参考'}.get(p['id'],p['title'].split(':')[0])
    if anchor:elems.append(Mark(p['id'],f"[{p['id']}] {short}"))
    elems.append(P(f"[{p['id']}] {subtitle or short} · {p['kind']}",'h2'))
    elems.append(P(p['hardware'],'small'))
    if not compact:elems.append(P(p['notes'],'small'))
    elems.append(metrics(p,rs));elems.append(Spacer(1,6))
    elems.append(P('能量与证据：'+p['boundary'],'small'))
    if compact:elems.append(P(p['notes'],'small'))
    if p['id'] in ['F01','F04']:elems.append(P('校核：'+' '.join(p.get('caveats',[])[:2]),'small'))
    elems.append(P(f'<link href="{escape(p["url"])}" color="#007E87">原论文 / 数据定位：{escape(clean(p["locator"]))}</link>','small',True))
    return elems

def make_chart():
    from reportlab.graphics.shapes import Drawing,String
    from reportlab.graphics.charts.lineplots import LinePlot
    from reportlab.graphics.widgets.markers import makeMarker
    drawing=Drawing(CW,270)
    for i,model in enumerate(['Qwen2-VL-2B','Qwen2.5-VL-3B','Qwen3-VL-2B']):
        rs=[r for r in byid['R01']['rows'] if r['model']==model and r['stage']=='decode']
        ox=i*CW/3; lp=LinePlot();lp.x=ox+32;lp.y=40;lp.width=CW/3-50;lp.height=177
        lp.data=[[(r['tps'],r['tpj'])] for r in rs];lp.joinedLines=0
        xmax=max(r['tps'] for r in rs)*1.3;ymax=max(r['tpj'] for r in rs)*1.3
        lp.xValueAxis.valueMin=0;lp.xValueAxis.valueMax=xmax;lp.yValueAxis.valueMin=0;lp.yValueAxis.valueMax=ymax
        for ax in [lp.xValueAxis,lp.yValueAxis]:
            ax.labels.fontName='CJK';ax.labels.fontSize=7;ax.strokeColor=colors.HexColor('#AABAC4');ax.gridStrokeColor=colors.HexColor('#E0E8ED')
        lp.yValueAxis.visibleGrid=True
        for j,col in enumerate(['#8794A3','#198B98','#33598A','#E89B34']):
            lp.lines[j].symbol=makeMarker('FilledCircle');lp.lines[j].symbol.fillColor=colors.HexColor(col);lp.lines[j].symbol.strokeColor=colors.HexColor(col);lp.lines[j].symbol.size=6
        drawing.add(lp)
        drawing.add(String(ox+32,247,model,fontName='CJKB',fontSize=11,fillColor=NAVY))
        drawing.add(String(ox+32,229,'Decode tokens/J',fontName='CJK',fontSize=8,fillColor=MUTED))
        drawing.add(String(ox+75,14,'Decode tokens/s',fontName='CJK',fontSize=8,fillColor=MUTED))
        for j,r in enumerate(rs):
            dx,dy=[(4,8),(4,8),(-42,11),(4,-12)][j]
            if model=='Qwen3-VL-2B' and j==2:continue
            label='W4A8 / W4A4' if model=='Qwen3-VL-2B' and j==3 else r['precision']
            if model=='Qwen3-VL-2B' and j==3:dx=-39;dy=12
            drawing.add(String(lp.x+r['tps']/xmax*lp.width+dx,lp.y+r['tpj']/ymax*lp.height+dy,label,fontName='CJK',fontSize=7,fillColor=INK))
    return drawing
chart=make_chart()

def make_story():
    s=[]
    def title(x,key=None):
        if key:s.append(Mark(key,x))
        s.append(P(x,'h1'))
    def text(x,style='body'):s.append(P(x,style))
    def page():s.append(PageBreak())
    s.append(Spacer(1,36));text('研究型硬件 · 可核对的模型与能量边界','h2')
    s.append(P('大模型推理\n速度与能效综述','big'))
    text('ASIC / CIM / PIM / FPGA / GPU','h2')
    text(f'32 项论文工作 · {len(allrows)} 组模型、配置与阶段记录 · tokens/s、tokens/J 与 J/token')
    text('范围已放宽：覆盖小于1B至百B级及MoE模型、多种数值精度与存储系统。科研加速器为主体，论文中的GPU实测作为参照。')
    text('本报告记录论文原始条件，不把架构仿真、芯片估计和板卡实测合并成性能排行榜。缺少可匹配能量的记录明确留空。')
    s.append(Spacer(1,15));text('检索与复核：2026-11-17（Asia/Shanghai） | 项目 Issue #261 / PR #262','small')
    text('本次新增111组 J/token：由同一记录的tokens/J取倒数，保留全部证据边界。无新服务器仿真、流片或板测。','small');page()
    title('指标与计算方法','method')
    text('J/token = 1 ÷ (tokens/J)，表示每个token消耗多少焦耳，越低越省能量；tokens/J是能效，越高越好。两者继承同一阶段、模型、batch和能量边界。')
    s.append(table(['指标','分子 / 分母','怎样解释'],[
      ['Decode 吞吐','生成的 token 数 / 对应 decode 时间','若从首个输出到末个输出计时，分子通常是 Nout-1 个间隔；按实际计时边界记录。'],
      ['Prefill 吞吐','处理的输入 token 数 / prefill 时间','完成条件：最后输入位置的 logits 就绪，后续 decode 所需 KV 可读取。视觉 token 与纯文本 token 分开。'],
      ['端到端生成吞吐','输出 token 数 / 整次请求时间','分母通常含 prefill；CENT 等原文使用输入+输出总数时，本报告另加 * 标记。'],
      ['阶段能效','相应 token 数 / 同窗口能量积分','能量 E=∫P(t)dt；分母与吞吐相同窗口且同边界时，tokens/J=(tokens/s)/W。'],
      ['每token能耗','J/token = E(J)/N = 1/(tokens/J)','同窗口功率与吞吐可配对时，也等于W/(tokens/s)。prefill的N是输入token；decode的N是输出token。'],
      ['原始延迟/能量换算','N×1000/t(ms)；N×1000/E(mJ)','decode单步N=1。只给TDP、TOPS/W、某算子pJ/MAC时，不推算整模型tokens/J。'],
    ],[105,220,CW-325]));s.append(Spacer(1,10))
    text('平均值的陷阱：mean(TPS)/mean(P) 不一定等于 token总数/总能量，更不一定等于 mean(TPS/P)。本文优先采用同测试点能量；CENT保留作者的专用聚合公式。')
    text('J/token一律从数据文件中尚未作显示舍入的tpj计算，显示约3位有效数字；原报整数或图读数的精度限制不变。其≈表示换算后的近似显示，并不新增实测证据。CENT沿用作者聚合能量，TerEffic沿用原报已舍入能效；平均能效的倒数不冒充逐请求能耗算术平均。','small')
    text('其他标记：原列≈为图读数；“条件换算”继承总体功耗未匹配同窗口的限制；“未报告”继续留空。功耗不默认包含DDR或主机。','small');page()
    title('代表结果速览：按条件阅读','overview')
    rows=[
     ['ProQuant [R01]','Qwen2.5-VL-3B W8A8','decode','8.00','2.03','芯片实测+DDR模型；V256+T256'],
     ['EdgeCIM [E01]','Llama3.2-3B INT4','decode','≈139.3','≈69.7','架构模型；B1；128/128；能量边界待核实'],
     ['VitaLLM [R03]','BitNet3B 三值','decode','70.7','1071.7*','芯片功耗换算；外部DDR未绑定'],
     ['TOM [R04]','BitNet2B 三值','峰值decode','3306.9','620.4*','固定ROM；5.33W总体功耗条件换算'],
     ['LEAP [A01]','Llama3-8B','端到端*','202.25','19.21','仿真；1024/1024；吞吐分子未明'],
     ['CENT [A02]','Llama2-7B BF16','decode','2850.5','14.00','8设备；B32；作者采样聚合'],
     ['TerEffic [F01]','MatMul-free 2.7B三值','decoder层','727','16','U280；B1；Vivado估算；非完整Transformer'],
     ['EdgeLLM [F03]','GLM-6B W4A16','峰值decode','85.8','1.51*','FPGA平均功耗配峰值；未含主机'],
     ['Hummingbird [F04]','Llama3-8B W4/KV8','decode','19.4','1.33','U250；B1；32/32；Vivado功耗'],
     ['Jetson AGX [G01]','Llama3.2-3B W4A16','decode','≈79.1','≈2.24','MAXN；扣空闲动态模块能效'],
     ['Coffee [A03]','Llama3.1-8B平均4bit','decode','153411','140.07','288加速器模型；B4096；1.4K/0.2K'],
     ['HNLPU [A04]','gpt-oss120B FP4','系统推理*','249960','36.226','16芯片；6.9kW；固定权重；阶段未拆分'],
    ]
    reps=[next(r for r in byid['R01']['rows'] if r['model']=='Qwen2.5-VL-3B' and r['precision']=='W8A8' and r['stage']=='decode'),
          next(r for r in byid['E01']['rows'] if r['model']=='Llama3.2-3B' and r['precision']=='INT4'),
          byid['R03']['rows'][0],byid['R04']['rows'][0],byid['A01']['rows'][0],byid['A02']['rows'][0],
          byid['F01']['rows'][4],byid['F03']['rows'][0],byid['F04']['rows'][2],byid['G01']['rows'][1],byid['A03']['rows'][0],byid['A04']['rows'][0]]
    for row,r in zip(rows,reps):row.insert(5,jfmt(r['j_per_token']))
    s.append(table(['工作','模型 / 精度','阶段','tokens/s','tokens/J','J/token','条件与限制'],rows,[100,145,70,68,60,70,CW-513]))
    text('* 表示正文还有统计或功耗边界限制。此表只用于定位，不代表同模型、同质量、同系统规模的优劣排序。详细表优先于此处舍入数。','small');page()
    title('同一平台内：低比特如何改变速度与能效','within')
    text('ProQuant 的三个模型均取相同 V256+T256 输入，以原表单步延迟和能量换算。三幅图各自展示同模型精度变化；坐标为 decode 输出指标。[R01]')
    s.append(chart)
    text('Qwen2.5-VL-3B 从 BF16 到 W8A8：约4.02→8.00 tokens/s，1.02→2.03 tokens/J；W4A4为16.01 tokens/s、4.05 tokens/J。数值约成比例，反映该工况下功率变化小、时延与能量共同下降。')
    text('这是一组硬件工作量比较；不同位宽的模型质量仍须回到论文质量表核查。Qwen3-VL-2B的W4A8与W4A4在此工况下数值重合。','small');page()
    for stage in ['decode','prefill']:
        title('ProQuant：'+('逐步解码' if stage=='decode' else '多模态预填充'))
        p=byid['R01'];rs=[r for r in p['rows'] if r['stage']==stage]
        s.extend(details(p,rs,subtitle=stage+' 逐模型数据',anchor=stage=='decode'))
        if stage=='decode':text('原始 ms/mJ 随附于数据文件；例如Qwen2.5-VL-3B W8A8：125.07 ms、492.73 mJ，速度=1000/125.07，能效=1000/492.73。','small')
        else:text('此页能量按视觉+文本输入token计，非生成token。例：Qwen2.5-VL-3B W8A8，512/1.5824=323.56输入tokens/s，512/2.69007=190.33输入tokens/J；2.69007/512≈0.00525 J/输入token。','small')
        page()
    title('两篇 VitaLLM：保留各自运行点')
    for id in ['R02','R03']:s.extend(details(byid[id],compact=True))
    page();title('固定权重 ROM：高吞吐依赖存储驻留')
    for id in ['R04','R05']:s.extend(details(byid[id],compact=True))
    page();title('PIM / NAND：原始能效与数据缺项')
    for id in ['R06','R07']:s.extend(details(byid[id],compact=True))
    page();title('混合存储与多模态：吞吐可用，能量仍需限定')
    for id in ['R08','E02']:s.extend(details(byid[id],compact=True))
    page()
    p=byid['E01']
    for prec in ['INT4','INT8']:
        title('EdgeCIM v1：'+prec+' 逐模型解码')
        s.extend(details(p,[r for r in p['rows'] if r['precision']==prec],anchor=prec=='INT4'))
        text('这里不是同一颗固定配置芯片跑所有模型的测量。不能把v2联合搜索的44.66 mm²直接配给每一行，也不将v2 273 GB/s条件自动赋给v1所有数据。','small');page()
    title('边缘 GPU：实测动态模块能效')
    s.extend(details(byid['G01']));page()
    title('RRAM PIM 与固定权重多芯片系统')
    for id in ['A01','A04']:s.extend(details(byid[id],compact=True))
    page();title('CENT：阶段、系统规模与聚合方法')
    s.extend(details(byid['A02']))
    text('复核来源：作者 processed_results.csv、run_sim.py、figure_15c.py；公开数据访问日2026-11-17，原值保存在随附JSON中。未重跑模拟器。','small')
    for label,u in [('原始数据','https://raw.githubusercontent.com/Yufeng98/CENT/main/cent_simulation/processed_results.csv'),('能效作图公式','https://github.com/Yufeng98/CENT/blob/main/figure_scripts/figure_15c.py')]:text(f'<link href="{u}" color="#007E87">{label}</link>','small') if False else s.append(P(f'<link href="{u}" color="#007E87">{label}</link>','small',True))
    page()
    p=byid['A03']
    for i,rs in enumerate([p['rows'][:6],p['rows'][6:]]):
        title('Coffee：'+('稠密模型' if i==0 else '更大模型与 MoE')+'的多加速器结果')
        s.extend(details(p,rs,anchor=i==0));page()
    title('数据中心 GPU：同篇论文中的实测参照')
    s.extend(details(byid['G02']));page()
    title('扩散 LLM：不能套用自回归 decode 定义')
    s.extend(details(byid['A05']))
    text('扩散语言模型会对一段输出反复去噪、更新或重用部分 token；应按最终完成输出token/全生成耗时及能量统计。内部迭代处理的token数不能算作新增输出token。')
    text('本表为两模型、五任务平均，不能用它推断每个模型都达到24.89 tokens/s。论文给出动态跳过和精度调整，需要同时核对任务质量。');page()
    title('FPGA：三值模型与片上/片外存储')
    s.extend(details(byid['F01']));page()
    title('FPGA：长上下文优化与 CPU 协同')
    for id in ['F02','F03']:s.extend(details(byid[id],compact=True))
    page();title('FPGA：DDR 平台上的逐 token 生成')
    s.extend(details(byid['F04']))
    text('原论文PW.Eff.把模型规模归一到7B后再除功耗。本报告从真实4.8/8.6/19.4 tokens/s和3.81/7.09/14.61 W重算，得到1.260/1.213/1.328 tokens/J。','small');page()
    title('FPGA：有绝对速度，缺少严格配对的能量')
    for id in ['F05','F06']:s.extend(details(byid[id],compact=True))
    page()
    missing=[p for p in papers if p.get('missing')]
    for start in range(0,len(missing),3):
        title('已有工作的保留项：能效与每token能耗缺项')
        for p in missing[start:start+3]:
            s.append(Mark(p['id'],f"[{p['id']}] {p['title'].split(':')[0]}"))
            text(f"[{p['id']}] {p['title']}",'h2');text(p['models']+' | '+p['hardware'],'small');text(p['notes'])
            s.append(P(f'<link href="{escape(p["url"])}" color="#007E87">来源：{escape(p["locator"])}</link>','small',True))
        page()
    title('跨论文比较：哪些结论能够成立','interpret')
    s.append(table(['比较轴','从本组文献能看到什么','应保留的条件'],[
      ['权重带宽','DDR逐token流式读权重通常受权重字节量与有效带宽限制；量化、batch复用、ROM驻留、PIM内带宽可减少外部传输。','B1且每token完整重读时，上限≈有效带宽/每token读字节；该公式不能套给固定ROM、稀疏或大batch结果。'],
      ['模型与数值精度','三值/低比特设计能大幅减少数据量；同平台ProQuant精度比较提供清楚配对。','BitNet、MatMul-free、Mamba、MoE、扩散LLM与标准dense Transformer不能只按参数数相除。'],
      ['功耗统计','芯片几十mW、板卡几十W、系统几kW均出现在文献中。','缺外部DRAM/主机能量会提高表面tokens/J；动态扣空闲与包含静态的数字也不等价。'],
      ['批量与时延','CENT/Coffee的总吞吐可以很高；batch扩大可复用权重。','总tokens/s不等于单流速度；应同时看batch、TPOT、上下文和输出长度。'],
      ['研究成熟度','综合、周期模拟、P&R、流片和整板实测各能回答不同问题。','工艺缩放与器件假设须显式保留。仅有P&R不意味着完成制造或板级推理。'],
    ],[95,300,CW-395]));s.append(Spacer(1,10))
    text('对项目后续benchmark：建议同时报告B1 decode、prefill、端到端三组tokens/s与tokens/J；固定checkpoint、tokenizer、精度、batch、输入输出长度、内存带宽及能量边界，再挑选同条件工作作比较。')
    text('若要从算子论文得到整模型指标，须补齐层数与张量尺寸、非线性与采样、KV及权重搬运、同步与调度，并对整个模型计时/积分。不能用GEMM加速比直接等同于LLM输出token加速比。');page()
    # Source index carries full original titles where supplied and internal links.
    order=['R01','R02','R03','R04','R05','R06','R07','R08','E01','E02','G01','A01','A02','A03','A04','A05','G02','F01','F02','F03','F04','F05','F06']+[p['id'] for p in missing]
    for start in range(0,len(order),9):
        title('论文索引与定位'+f' · {start//9+1}')
        rows=[]
        for id in order[start:start+9]:
            p=byid[id];pg=previous_pages.get(id,'-')
            rows.append([f'[{id}] · p.{pg}',p['title'],p['locator'],p['url']])
        # Links inside table cells; build separately to retain clickable destinations.
        d=[[P(x,'head') for x in ['索引 / 详表页','论文 / 来源','版本与图表','原文链接']]]
        for row in rows:
            id=row[0].split(']')[0][1:]
            d.append([P(f'<link href="#{id}" color="#007E87">{escape(row[0])}</link>','cell',True),P(row[1],'cell'),P(row[2],'cell'),P(f'<link href="{escape(row[3])}" color="#007E87">{escape(row[3])}</link>','cell',True)])
        t=Table(d,colWidths=[83,300,180,CW-563],repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]));s.append(t)
        if start+9<len(order):page()
    page();title('数据追溯与更正记录','audit')
    text('本报告接续项目Issue #261 / PR #262。旧版21篇ASIC调研保留，本版将范围扩大至32项论文工作；GPU参照复用EdgeCIM和Coffee论文，不重复计为新论文。')
    text(f'数据文件含{len(allrows)}行阶段/模型/配置记录，其中{sum(r["tpj"] is not None for r in allrows)}行有原报、换算或条件能效，均新增J/token倒数值；其余22行留空。CHIME仅对作者总体区间取倒数，不分配到模型；DynaTE保留跨模型聚合标签。')
    s.append(table(['本次核对发现','报告处理'],[
      ['EdgeCIM不同版本图例与数据','速度和能效使用v1配对；GPU采用v2实测，明确版本与边界。'],
      ['VitaLLM长版能效与速度/功耗不一致','原文1098.38保留在备注；表中以70.70/0.06597=1071.70作明确换算。'],
      ['CHIME总体功耗与分项图不一致','不把总体2W强配所有模型；不生成可靠逐模型tokens/J。'],
      ['CENT各列统计窗口不同','沿用作者作图公式从mJ/token换算，保留原始TPS和功率。'],
      ['Hummingbird能效列已归一模型大小','从真实速度与功率重新计算tokens/J，不沿用归一化PW.Eff.。'],
      ['PALUTE、TerEffic的特殊前提','保留PALUTE器件假设与不完整工况；TerEffic标decoder层和RNN变体，均不当标准dense LLM整机实测。'],
    ],[230,CW-230]));s.append(Spacer(1,10))
    text('来源均为论文、作者项目或作者公开数据；引用版本和访问日期见索引与随附JSON。作者仓库main链接可能变化，本次提取原值已保存在本地报告数据中。未开展新的服务器仿真或测量。')
    text('本次J/token补充基于交付commit 33c9743b8a50362501accb56bba08796e6e0f88d；研究分支task/261-llm-asic-benchmarks。待独立审查，不代表芯片物理验收或PR已合并。','small')
    return s

pages={};previous_pages={}
pdf=OUT/'issue-261-llm-speed-energy-report.pdf'
for _ in range(2):
    pages={}
    doc=SimpleDocTemplate(str(pdf),pagesize=PAGE,rightMargin=M,leftMargin=M,topMargin=43,bottomMargin=38,title='大模型推理速度与能效综述',author='Melodydt / LLMHardwareDesign',pageCompression=1)
    doc.build(make_story(),onFirstPage=onpage,onLaterPages=onpage)
    previous_pages=pages.copy()
reader=PdfReader(pdf)
textall='\n'.join(p.extract_text() or '' for p in reader.pages)
assert len(allrows)==133,len(allrows)
assert all(p['id'] in textall for p in papers)
assert all(r['tps'] is not None and r['tps']>0 for r in allrows)
assert all(r['tpj'] is None or r['tpj']>0 for r in allrows)
assert sum(r['j_per_token'] is not None for r in allrows)==111
for r in allrows:
    assert (r['j_per_token'] is None)==(r['tpj'] is None)
    if r['tpj'] is not None:assert math.isclose(r['j_per_token']*r['tpj'],1,rel_tol=1e-12)
for r in byid['R01']['rows']:
    assert abs(r['tps']*r['latency_ms']/1000-r['numerator_tokens'])<1e-7
    assert abs(r['tpj']*r['energy_mj']/1000-r['numerator_tokens'])<1e-7
    assert math.isclose(r['j_per_token'],r['energy_mj']/1000/r['numerator_tokens'],rel_tol=1e-12)
for r in byid['A02']['rows']:
    assert math.isclose(r['j_per_token'],r['energy_per_token_mj']/1000,rel_tol=1e-12)
manifest=dict(date='2026-11-17',pages=len(reader.pages),records=len(allrows),efficiency_rows=sum(r['tpj'] is not None for r in allrows),j_per_token_rows=sum(r['j_per_token'] is not None for r in allrows),source_entries=len(papers),distinct_paper_works=32,
  external_links=sum(a.get_object().get('/A',{}).get('/URI') is not None for p in reader.pages for a in p.get('/Annots',[])),
  pdf_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),page_map=pages,
  source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCES.glob('*.json')},
  generator_sha256={n:hashlib.sha256((BASE/n).read_bytes()).hexdigest() for n in ['build_report.py','root_data.py']},
  versions={'python':sys.version,'reportlab':__import__('reportlab').Version,'pypdf':__import__('pypdf').__version__},checks='133 source/record checks, 111 reciprocal conversions, 24 ProQuant raw-energy checks and 9 CENT raw-energy checks passed; visual QA recorded in delivery note')
(OUT/'issue-261-llm-speed-energy-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(BASE/'extracted_report.txt').write_text(textall,encoding='utf-8')
print(json.dumps({k:manifest[k] for k in ['pages','records','efficiency_rows','source_entries','pdf_sha256','external_links']},ensure_ascii=False))
print('PDF',pdf)
