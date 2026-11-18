"""Generate matching seven-model 300/200 MHz speed and power PDFs."""
from pathlib import Path
from hashlib import sha256
from xml.sax.saxutils import escape
import json
from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,PageBreak,Spacer
from pypdf import PdfReader
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
OPT={
'qwen3':'三P FFN；注意力分片与双窗口，P512保留代表层映射。',
'llama':'64维紧凑KV、256B行与V读取复用；保留自身上下文曲线。',
'granite':'top-8/40专家按3/3/2分给三P；专家Mid驻留本地SRAM，注意力增长与专家路由分开。',
'phi':'融合QKV及Gate/Up、128维ATT1、V流水及partial LongRoPE。',
'gemma':'256维宽注意力、Q12残差及后归一化，保留局部/全局注意力和GELU路径。',
'qwen35':'8个ATT与24个GDN层，历史通过DDR显式恢复；一个共享8-lane R替换状态代理。',
'falcon':'32层Mamba2后串行ATT；递推维度固定，一个共享8-lane R替换状态代理。'}
SPECIAL={
'qwen3':'未覆盖/未验收：独立长序列活动、完整浮点转换与部署。',
'llama':'未覆盖/未验收：真实长上下文序列及形状迁移误差、完整浮点转换与部署。',
'granite':'未覆盖/未验收：自然长提示的专家路由分布、状态驻留与争用；强制路由样本不是自然分布。',
'phi':'未覆盖/未验收：长上下文非线性、完整LongRoPE路径与全序列误差。',
'gemma':'未覆盖/未验收：GELU仍为运算级代理，格式转换、完整候选周期及全序列精度。',
'qwen35':'未覆盖/未验收：独立层/非零Prefill活动、定点转换与模型精度、R实际调度/加载/门控；P512的R活动只有冷状态外推。',
'falcon':'未覆盖/未验收：外部delta×value注入仍为代理；独立层/非零Prefill、格式转换、R实际调度/加载/门控及完整模型精度。'}
GAPS='共同未覆盖/未验收：完整物理top/provider、原生ABI与实际路由/门控、完整RTL控制状态、全局时钟及跨块互连、DDR PHY/封装/板级。布线寄生按本路线排除；300MHz时序未闭合，200MHz亦未签核。'
def grouped(w):
    x=w['components_j'];groups={k:[0.,0.] for k in ['M计算/驻留','512-bit数据SRAM','控制/PM/参考互连','公共算术/驻留','其他特殊算术代理','递推R候选及注入','写DMA']}
    for k,v in x.items():
        g='递推R候选及注入' if k.startswith('recurrent_') else 'M计算/驻留' if k.startswith('m_') else '512-bit数据SRAM' if k.startswith('s_p_') else '写DMA' if k.startswith('write_dma_') else '其他特殊算术代理' if k.startswith('proxy_') else '公共算术/驻留' if k.startswith(('rms_','measured_','arithmetic_','chunk_','g32_','u_add')) else '控制/PM/参考互连'
        for i in (0,1):groups[g][i]+=v[i]
    groups['读DMA（四方案包络）']=[w['scopes']['on_chip']['energy_j_per_window'][i]-w['base_on_chip_j'][i] for i in (0,1)]
    groups['DDR器件']=[w['ddr_j']]*2
    return groups
def render(freq,d,v):
    freq=str(freq);path=ROOT/'output/pdf'/('seven-model-'+freq+'mhz-v5-r-narrowed.pdf');path.parent.mkdir(parents=True,exist_ok=True)
    pdfmetrics.registerFont(TTFont('CN','C:/Windows/Fonts/Deng.ttf'));pdfmetrics.registerFont(TTFont('CNB','C:/Windows/Fonts/Dengb.ttf'));rl_config.invariant=1
    body=ParagraphStyle('body',fontName='CN',fontSize=9.6,leading=14,spaceAfter=8,wordWrap='CJK',textColor=colors.HexColor('#183044'))
    title=ParagraphStyle('title',parent=body,fontName='CNB',fontSize=20,leading=27,spaceAfter=12)
    small=ParagraphStyle('small',parent=body,fontSize=8.3,leading=11.6,spaceAfter=7)
    cell=ParagraphStyle('cell',parent=small,fontSize=8,leading=11,spaceAfter=0)
    section=ParagraphStyle('section',parent=body,fontName='CNB',fontSize=12,leading=17,spaceAfter=8)
    story=[];numbers=[];pages=0
    def p(s,style=body):story.append(Paragraph(escape(str(s)).replace('\n','<br/>'),style))
    def page(s):
        nonlocal pages
        if pages:story.append(PageBreak())
        pages+=1;p(s,title);p('SYNC-08 | '+d['created_at'][:19]+' +08 | '+freq+' MHz | 512-bit SRAM / 三P',small)
    def n(x,dec=3):
        if isinstance(x,list):return ' - '.join(n(a,dec) for a in x)
        s=f'{x:.{dec}f}';numbers.append(s);return s
    def table(head,rows,width,pad=5):
        t=Table([[Paragraph(escape(str(x)),cell) for x in row] for row in [head]+rows],colWidths=width,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e6f0f2')),('LINEBELOW',(0,0),(-1,0),.8,colors.HexColor('#006c70')),('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#cbd8df')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),pad),('BOTTOMPADDING',(0,0),(-1,-1),pad)]))
        story.extend([t,Spacer(1,8)])
    def w(m,phase):return m['windows'][phase]['frequencies'][freq]
    page(freq+' MHz：七模型速度与功耗')
    p('统一使用最新v5 E32-18基线；Qwen3.5和Falcon采用收窄后的递推R候选。包含一个读DMA，片上与片上+DDR分别报告。Prefill为512输入token外推并含末次词表头；Decode为代表性512历史起点测试中的第二步。')
    p('300MHz时间来自已验收短窗和最新P512外推；本版300MHz数值与上一轮收窄结果一致。' if freq=='300' else '200MHz由既有配对频率采样/直接200MHz上下文曲线迁移到最新v5时间，再逐项重算能量。本轮没有新增E32-18整模型200MHz回放，不能视作200MHz实测。')
    table(['模型','P512 token/s','P512总时长 s','Decode token/s','Decode ms/token'],[[m['name']+(' *' if m['model'] in ('qwen35','falcon') else ''),n(w(m,'prefill512')['tokens_per_second']),n(w(m,'prefill512')['duration_s']),n(w(m,'decode')['tokens_per_second']),n(w(m,'decode')['duration_s']*1000)] for m in d['models']],[135,90,90,90,90])
    p('* R候选数值与调度尚未整模型验收。速度保留v5调度的频率估计；候选单R累计服务时间满足窗口预算，但这只是实现吞吐的必要条件。P512没有完整序列实跑或误差验证。',small)
    p('读表口径',section)
    p('速度单位token/s；平均功率W=窗口能量/窗口时长；能耗mJ/token=窗口能量/输入或输出token数。Prefill除以512，Decode除以1。低高值来自标定样本/部署情景，不是统计置信区间或保证误差界。')
    p('电压和温度保持不变，DDR周期始终630ps。四种读DMA是互斥方案，phase已包含shared。主表只替换两模型的状态代理；其他特殊算子保持v5默认覆盖，没有额外叠加特殊候选组合。',small)
    page('双口径能耗与平均功率')
    for phase,label in [('prefill512','P512外推：每输入token'),('decode','Decode2：每输出token')]:
        p(label,section)
        table(['模型','片上 mJ/token','片上+DDR mJ/token','片上 W','片上+DDR W'],[[m['name'],n(w(m,phase)['scopes']['on_chip']['energy_mj_per_token']),n(w(m,phase)['scopes']['on_chip_plus_ddr']['energy_mj_per_token']),n(w(m,phase)['scopes']['on_chip']['average_power_w']),n(w(m,phase)['scopes']['on_chip_plus_ddr']['average_power_w'])] for m in d['models']],[112,99,110,87,87],pad=5)
    p('能耗包含当前条件小计；未覆盖项见逐模型页。DDR仅指器件，未包含PHY/封装/板级。两模型的R状态存于触发器，和512-bit系统数据SRAM分开计费。',small)
    page('频率迁移方法与验证边界')
    p('时间：对每个Prefill位置，将最新300MHz时长乘既有200/300对应位置比值；启动保留在首位置，末次head独立缩放且只计一次。Decode采用先前配对完整层重建的T200/T300比值。保留三P并行及DDR重叠，不把每P忙时相加。',small)
    p('能量：固定事件次数及同电压/温度事件成本；驻留功率按P200=(P300-Pleak)×2/3+Pleak，再乘新时长。M忙时增量使用旧配对响应。DDR命令能量与后台/刷新功率分别迁移。读DMA动态每64B成本固定、静默功率按漏电分离。2/3沿用名义频率约定，时钟时长用3334/5000ps。',small)
    p('两模型状态：先删除GDN/Mamba状态代理，再用对应频率已有全引脚活动标定加入LOAD/EXEC/读回动态能量和一个R的整窗静默。Falcon外部注入仍用E32代理；P512状态活动仍是冷状态样本外推。',small)
    table(['模型','迁移后的时长比 P512','时长比 Decode','另一迁移法时长差 % P512 / Decode'],[[m['name'],n(m['windows']['prefill512']['time_ratio'],4),n(m['windows']['decode']['time_ratio'],4),n(m['timing']['migration_sensitivity_percent']['prefill512'],3)+' / '+n(m['timing']['migration_sensitivity_percent']['decode'],3)] for m in d['models']],[133,107,107,148],pad=4)
    p('敏感性对照：旧200MHz曲线加上最新v5相对旧300MHz的时长增量×5000/3334。两法差值小不证明真实误差小；旧采样主要是E32-9，最新基线E32-18。没有新200MHz配对回放，因此旧频率响应迁移仍待验证。该敏感性未混入主表能耗范围。',small)
    p('版本：PR281 e29d72a5；PR294 01141df7；R候选PR295 ceca86ef，收窄回执6dd7e42b。'+str(v['frozen_inputs'])+'个输入SHA、'+str(v['numeric_checks'])+'项关系通过，300MHz各范围与原件对齐。无新服务器作业；无综合、物理时序或完整序列验收。',small)
    for offset in range(0,7,2):
        page('逐模型覆盖小计 '+str(offset+1)+'-'+str(min(offset+2,7)))
        for m in d['models'][offset:offset+2]:
            p(m['name'],section);p('采用的优化：'+OPT[m['model']],small)
            a,b=w(m,'prefill512'),w(m,'decode');ga,gb=grouped(a),grouped(b)
            table(['分项（mJ/token）','P512','Decode2'],[[k,n([x*1000/512 for x in ga[k]]),n([x*1000 for x in gb[k]])] for k in ga],[221,137,137],pad=3)
            p(SPECIAL[m['model']],small)
        p(GAPS,small)
    def footer(c,doc):
        c.setStrokeColor(colors.HexColor('#006c70'));c.line(45,35,550,35);c.setFont('CN',8)
        c.drawString(45,22,'SYNC-08 | '+freq+' MHz条件估算 | 非完整芯片实测');c.drawRightString(550,22,str(doc.page))
    SimpleDocTemplate(str(path),pagesize=A4,leftMargin=45,rightMargin=45,topMargin=42,bottomMargin=49).build(story,onFirstPage=footer,onLaterPages=footer)
    doc=PdfReader(path);assert len(doc.pages)==pages,(freq,len(doc.pages),pages)
    text=''.join(p.extract_text() or '' for p in doc.pages);assert all(x in text for x in numbers)
    return dict(frequency_mhz=int(freq),file=path.relative_to(ROOT).as_posix(),pages=pages,sha256=sha256(path.read_bytes()).hexdigest(),numeric_values=len(numbers),visual_review='pending')
def main():
    d=json.loads((H/'results.json').read_bytes());v=json.loads((H/'verification.json').read_bytes());assert v['passed'] and sha256((H/'results.json').read_bytes()).hexdigest()==v['results_sha256']
    records=[render(f,d,v) for f in (300,200)]
    (H/'pdf-checks.json').write_text(json.dumps(records,indent=2)+'\n');print(json.dumps(records,indent=2))
if __name__=='__main__':main()
