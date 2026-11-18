"""Latest 300 MHz seven-model report with explicit recurrent candidate replacement."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone,timedelta
from xml.sax.saxutils import escape
import json,sys
from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,PageBreak,Spacer
from pypdf import PdfReader
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'report-sync'))
from render_sync06 import ORDER,NAMES,OPT,GAPS,dma_envelope,short_dma
def main():
    data=json.loads((HERE/'candidate-rollup.json').read_bytes());validation=json.loads((HERE/'verification.json').read_bytes());assert validation['passed']
    base=json.loads((HERE/'inputs/output/pdf/seven-model-sync06-20261118-r2/frequency-estimates.json').read_bytes())
    bymodel={m['model']:m for m in data['models']};jobs=json.loads((HERE/'jobs.json').read_bytes())
    status=json.loads((HERE/'status.json').read_bytes());assert all(j['job']+'|' in status['sacct'] for j in jobs.values())
    assert status['sacct'].count('COMPLETED')==2 and status['sacct'].count('0:0|UNLIMITED')==2
    out=ROOT/'output/pdf/seven-model-recurrent-300mhz-v1.pdf';out.parent.mkdir(exist_ok=True,parents=True)
    pdfmetrics.registerFont(TTFont('CN','C:/Windows/Fonts/Deng.ttf'));pdfmetrics.registerFont(TTFont('CNB','C:/Windows/Fonts/Dengb.ttf'));rl_config.invariant=1
    body=ParagraphStyle('body',fontName='CN',fontSize=10,leading=15,spaceAfter=9,wordWrap='CJK',textColor=colors.HexColor('#183044'))
    title=ParagraphStyle('title',parent=body,fontName='CNB',fontSize=21,leading=28,spaceAfter=14)
    small=ParagraphStyle('small',parent=body,fontSize=8.4,leading=12.2);cell=ParagraphStyle('cell',parent=small,fontSize=8,leading=11.5,spaceAfter=0)
    story=[];pages=0;expected=[];now=datetime.now(timezone(timedelta(hours=8))).isoformat()
    def p(s,style=body):story.append(Paragraph(escape(str(s)).replace('\n','<br/>'),style))
    def page(s):
        nonlocal pages
        if pages:story.append(PageBreak())
        pages+=1;p(s,title);p('SYNC-07-R300 | '+now[:19]+' +08 | 综合后、无布线寄生条件估算',small)
    def n(x,d=3):
        if isinstance(x,(list,tuple)):return ' - '.join(n(v,d) for v in x)
        text=f'{x:.{d}f}';expected.append(text);return text
    def table(head,rows,width):
        t=Table([[Paragraph(escape(str(v)).replace('\n','<br/>'),cell) for v in row] for row in [head]+rows],colWidths=width,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e6f0f2')),('LINEBELOW',(0,0),(-1,0),.8,colors.HexColor('#006c70')),('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#cbd8df')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
        story.append(t);story.append(Spacer(1,8))
    def window(m,phase):
        if m in bymodel:
            w=bymodel[m]['windows'][phase];return dict(tokens=w['tokens'],duration_s=w['duration_s'],tokens_per_second=w['tokens_per_second'],scopes=w['dma_candidate_envelope'])
        w=base['current']['300'][m]['windows'][phase]
        return dma_envelope(w if phase=='prefill512' else short_dma(base,m,phase))
    def energy(w,s):return n([v*1000 for v in w['scopes'][s]['energy_j_per_token']])
    def watts(w,s):return n(w['scopes'][s]['average_power_w'])
    page('最新300 MHz：状态代理收窄')
    p('本版将Qwen3.5和Falcon的GDN/Mamba状态更新代理替换为匹配300 MHz时基的候选R活动成本；其余五模型不变。七模型均采用v5 E32-18时间、512-bit数据SRAM、三P；DDR保持630 ps。')
    table(['第二步Decode','原含DMA\n片上mJ/token','替换后含DMA\n片上mJ/token','区间宽度\n缩小 %'],[[m['name'],n(m['windows']['decode']['dma_baseline_envelope']['on_chip']['energy_mj_per_token']),n(m['windows']['decode']['dma_candidate_envelope']['on_chip']['energy_mj_per_token']),n(m['windows']['decode']['interval_width_reduction_percent']['including_read_dma'],2)] for m in data['models']],[121,139,139,96])
    p('包含一个读DMA的四种互斥场景包络。收窄来自替换宽范围状态代理；不是统计置信区间或完整模型误差界，也没有缩窄其他缺项的假设。')
    table(['模型','P512估计\ntoken/s','Decode2\ntoken/s','P512片上+DDR\nmJ/token','Decode2片上+DDR\nmJ/token'],[[NAMES[m]+(' *' if m in bymodel else ''),n(window(m,'prefill512')['tokens_per_second']),n(window(m,'decode')['tokens_per_second']),energy(window(m,'prefill512'),'on_chip_plus_ddr'),energy(window(m,'decode'),'on_chip_plus_ddr')] for m in ORDER],[129,73,73,110,110])
    p('* 两模型为R候选替换场景；速度仍是已验收的v5 TLM值，尚未把候选服务周期安装到整模型调度。完整P512仍为外推；R的Prefill活动仅来自冷状态样本。',small)
    page('七模型双口径功率与能耗')
    for phase,label in [('prefill512','P512：512输入token，启动/末次词表头各一次'),('decode','Decode2：代表性512历史起点测试中的第二步')]:
        p(label,small)
        table(['模型','片上mJ/token','片上+DDR mJ/token','片上W','片上+DDR W'],[[NAMES[m]+(' *' if m in bymodel else ''),energy(window(m,phase),'on_chip'),energy(window(m,phase),'on_chip_plus_ddr'),watts(window(m,phase),'on_chip'),watts(window(m,phase),'on_chip_plus_ddr')] for m in ORDER],[113,98,108,88,88])
    p('以上均包含一个读DMA；phase已包含shared，禁止叠加。DDR项只覆盖器件，不含PHY/封装/板级。R候选与默认值有独立账本，未宣称整模型RTL或FP32等价。',small)
    for m in data['models']:
        key='qwen35' if m['model']=='qwen35' else 'falcon-wide';cal=json.loads((HERE/(key+'-calibration.json')).read_bytes())
        page(m['name']+'：替换及剩余范围')
        p('仅删除 '+m['proxy_removed']+'，加入一个共享8-lane R的完整装载、执行和读回动态增量及整窗静默驻留；原DDR、SRAM、控制及其他算术保留。',small)
        table(['窗口','原片上mJ/token\n含一个读DMA','替换后片上mJ/token\n含一个读DMA','替换后片上+DDR\nmJ/token'],[[label,n(w['dma_baseline_envelope']['on_chip']['energy_mj_per_token']),n(w['dma_candidate_envelope']['on_chip']['energy_mj_per_token']),n(w['dma_candidate_envelope']['on_chip_plus_ddr']['energy_mj_per_token'])] for phase,label in [('prefill','短P2'),('first_token','首Decode'),('decode','Decode2'),('prefill512','P512外推')] for w in [m['windows'][phase]]],[80,138,138,139])
        w=m['windows']['decode']
        table(['Decode2替换项','数值'],[['16通道服务次数',str(w['calls_16channel'])],['删除的原状态代理 mJ/token',n([v*1000 for v in w['removed_proxy_j']])],['新R+驻留+保留注入 mJ/token',n([v*1000 for v in w['replacement_j']])],['R每16通道动态增量 nJ',n([min(w['increment_j_per_16channel'])*1e9,max(w['increment_j_per_16channel'])*1e9])],['R静默功率 W',n(w['shared_r_idle_w'],6)],['单R累计服务时间 / 原窗口 s',n(w['one_r_active_time_s'],6)+' / '+n(w['duration_s'],6)],['不含读DMA时的范围宽度缩小 %',n(w['interval_width_reduction_percent']['base'],2)]],[240,255])
        p('沿用专项调度：'+OPT[m['model']],small)
        p('仍缺少：独立层/长序列及非零Prefill采样，FP32转换/provider和模型精度，实际R部署、加载路径、调度和门控。'+('Falcon外部delta×value注入继续保留E32代理。' if key=='falcon-wide' else 'Qwen的定点数值验收范围仍限于此前样本。'),small)
        p('单R服务时间小于窗口仅是必要条件，不证明原吞吐可由候选实现。'+GAPS,small)
    page('300 MHz标定方法与覆盖')
    p('原两套综合网表和完整门级事件来自已通过数值检查的200 MHz候选。因原活动为零延迟且只在时钟边沿变化，本轮严格把每个2500 ps半周期映射为1667 ps，再以3.334 ns时钟重新运行OpenROAD功耗分析。事件值、顺序、引脚声明、Liberty和0.05 ns输入跃迁保持不变。')
    table(['模型','单元数','每窗完整标注引脚','配对窗口','时基'],[[m['name'],str(json.loads((HERE/(('qwen35' if m['model']=='qwen35' else 'falcon-wide')+'-calibration.json')).read_bytes())['source']['cell_count']),str(json.loads((HERE/(('qwen35' if m['model']=='qwen35' else 'falcon-wide')+'-calibration.json')).read_bytes())['expected_annotated_pins']),'12对','3334 ps'] for m in data['models']],[144,88,111,73,79])
    p('分别重算活跃与等长静默功率，以差值乘窗口时间得到服务动态能量。按两个16通道捕获块的端点外推服务次数；一个R的静默功率乘完整模型窗口，再加入尚未实现的Falcon注入代理。不是直接把旧200 MHz整模型功率乘1.5。')
    p('短P2/首Decode/Decode2的服务计数来自原算术审计，并核验v5数值/流量验收和状态代理能量不变。P512状态次数按每token固定工作外推，启动/词表头没有状态服务；其状态活动仍只有冷样本，不表示已测得长序列的活动上下界。',small)
    p('R内部状态由触发器保存，与系统512-bit数据SRAM分开计费。同一固定映射在300 MHz理想时基下重算功耗，本轮没有重新综合或物理时序签核。无SDF、无寄生，不据此消除M或R的真实时序风险。',small)
    p('区间剩余来源包括其他特殊算术代理、算术静默/staging情景、DMA方案和活动样本差异。收窄一个代理不等于补齐所有物理覆盖。',small)
    page('四DMA方案与特殊组合候选')
    for m in data['models']:
        w=m['windows']['decode'];p(m['name']+' / Decode2',small)
        table(['方案（互斥）','R替换片上\nmJ/token','R替换片上+DDR\nmJ/token','特殊候选+R\n片上+DDR mJ/token'],[[v,n(s['on_chip']['energy_mj_per_token']),n(s['on_chip_plus_ddr']['energy_mj_per_token']),n(w['special_dma_candidate'][v]['on_chip_plus_ddr']['energy_mj_per_token'])] for v,s in w['dma_candidate'].items()],[118,120,128,129])
    p('主表采用仅替换状态代理的R场景。最右列同时沿用v5的Conv4/EXP/sigmoid/softplus等去重替换；先删除对应旧代理再加候选，不与原默认代理相加。两种候选的完整数值、转换与周期接入仍未完成。')
    p('每个模型的JSON同时保存基础、四种DMA、特殊替换及其与R组合的前后结果；应在相同方案、覆盖和时间窗口内比较。未唯一绑定读DMA物理部署，不能把跨方案最低值称为已实现硬件。',small)
    page('版本、验证与下一步')
    table(['来源','提交/证据'],[['新v5时间/功耗','PR281 / e29d72a585dd1fb0cde6c9a6976ef0fe78f98f96'],['P512外推第3版','PR294 / 01141df70d358c4a4225e36f153b695ced1d05b1'],['本轮标定源码','PR295 / '+data['source']['source_commit']],['运行','120432 Qwen3.5、120433 Falcon；各12核、UNLIMITED；真实终态见status.json'],['验证',str(validation['paired_power_windows_verified'])+'个功耗窗、'+str(validation['numeric_checks'])+'项独立数值关系、'+str(validation['input_sha256_verified'])+'个输入SHA']],[135,360])
    p('本轮结果已通过：原件/输出哈希、事件与时基守恒、全引脚标注、代理先删后加、单DMA互斥、DDR保持不变、能量/功率/每token单位和服务预算检查。管理结构检查仅证明仓库管理文件有效。',small)
    p('后续按顺序：1. 扩展独立层、非零Prefill和真实长序列活动；2. 验证定点候选的模型输出精度、转换与Falcon注入；3. 确定R实例/装载/状态存储/门控并接入调度；4. 重算候选时间后再次积分；5. 如需物理口径，再补时序/寄生/全局互连及PHY；6. 独立审查与合并。')
    p('200 MHz报告和原始候选数据不变。默认主线账本保持原件，本版是匹配最新300 MHz基线的明确候选场景。没有完整512-token实跑，也没有新增整模型RTL/物理验收。',small)
    p('规则rayggxia-project-collab 1.0.0；负责人Melodydt；Issue280保持in_progress，PR295待独立审查、未合并。登记PR5 pending；Projects配置/工具缺失，条目unverified、同步pending。未配置聊天结束后自动监测。',small)
    def footer(c,doc):
        c.setStrokeColor(colors.HexColor('#006c70'));c.line(45,36,550,36);c.setFont('CN',8)
        c.drawString(45,23,'SYNC-07-R300 | 两模型递推候选替换 | 512-bit SRAM');c.drawRightString(550,23,str(doc.page))
    SimpleDocTemplate(str(out),pagesize=A4,leftMargin=45,rightMargin=45,topMargin=44,bottomMargin=48).build(story,onFirstPage=footer,onLaterPages=footer)
    reader=PdfReader(out);assert len(reader.pages)==pages,(len(reader.pages),pages)
    text=''.join(p.extract_text() or '' for p in reader.pages);assert all(x in text for x in expected)
    (HERE/'pdf-validation.json').write_text(json.dumps(dict(file=out.relative_to(ROOT).as_posix(),sha256=sha256(out.read_bytes()).hexdigest(),pages=pages,numeric_values_checked=len(expected),visual_review='pending',generated_at=now),indent=2)+'\n')
    print('PDF_BUILT',pages,len(expected),out)
if __name__=='__main__':main()
