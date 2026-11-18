"""Rolling v4 report: preserved arithmetic plus qualified control estimates."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,PageBreak,Spacer
from build_energy_report import COMPONENTS
from build_arithmetic_energy_report import MODELS,NAMES,WINDOWS,LABELS,fmt

HERE=Path(__file__).resolve().parent
CONTROL={
 'native_mother_core_actual_parameter_reference':'母控核心（替换旧参考）',
 'local_shell_dispatch_reference_4x':'四局控外壳 + 四调度器',
 'mother_pm_runtime_fetch_increment':'母控 PM 运行取指增量',
 'cohort_switch_active_increment':'控制交换机活跃增量'}
EXCLUDED='未覆盖：母控核心外的镜像安装/序列/仲裁及报文桥；未采样状态与精确驻留，各模型路由表差异和真实门控，全局时钟/跨块互连，读 DMA 静默/漏电与实测动态，DDR PHY/封装/板级 I/O。布线寄生主动排除。特殊算子代理不是匹配 RTL 验收。'
def cfmt(v):
    return ('%.6f - %.6f' if max(v)<0.001 else '%.3f - %.3f')%(v[0],v[1])


def main(output=None):
    if output is None:
        ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=Path('output/pdf/seven-model-energy-evaluation.pdf'));output=ap.parse_args().output
    pdfmetrics.registerFont(TTFont('CN','C:/Windows/Fonts/Deng.ttf'))
    pdfmetrics.registerFont(TTFont('CNB','C:/Windows/Fonts/Dengb.ttf'));rl_config.invariant=1
    body=ParagraphStyle('body',fontName='CN',fontSize=9.4,leading=13.5,spaceAfter=7,wordWrap='CJK')
    title=ParagraphStyle('title',parent=body,fontName='CNB',fontSize=21,leading=27,spaceAfter=14)
    heading=ParagraphStyle('head',parent=body,fontName='CNB',fontSize=12.5,leading=17,spaceAfter=9)
    small=ParagraphStyle('small',parent=body,fontSize=8,leading=10.7)
    records={m:json.loads((HERE/(m+'_tlm_power_v4_control.json')).read_bytes()) for m in MODELS}
    idx=json.loads((HERE/'energy_report_models.json').read_bytes());meta={x['result'].split('_tlm_power')[0]:x for x in idx['models']}
    story=[]
    def p(text,style=body):story.append(Paragraph(escape(text),style))
    def table(rows,widths):
        t=Table([[Paragraph(escape(str(v)),small) for v in row] for row in rows],colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DAE9ED')),('VALIGN',(0,0),(-1,-1),'TOP'),
          ('GRID',(0,0),(-1,-1),.3,colors.HexColor('#BCCDD2')),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
          ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]));story.extend([t,Spacer(1,10)])
    p('七模型能耗评估',title);p('v4：控制补项与母控参数纠正',heading)
    p('2026-11-18 | Issue #280 / 草稿 PR #281 | Melodydt')
    p('片上与片上 + DDR 分别报告。固定 512-bit 数据 SRAM、三 P 并行 FFN、代表性 KV 历史、短 Prefill 与两步 Decode、名义 300 MHz。冻结时间、输出与 DDR 数据不变。')
    p('本版新增局控外壳/调度、母控 PM 运行取指和控制交换机活跃增量，并按真实 SERVICE_STALL_LIMIT=2,000,000 替换此前误用 4,096 的母控核心参考。母控启动窗已经采样，核心按全窗参考计入一次。')
    p('这是综合或保留既有单元网络的无布线寄生条件估算。C639 样本迁移到各模型；整模型控制活动、每模型路由表、部署门控未全部实现或校准。范围不是统计置信区间，也不是已证明的最坏误差界。')
    p('本轮四个最终作业',heading)
    table([['作业','内容','结果'],['120297','交换机六窗','COMPLETED 0:0'],['120300','4 外壳 + 4 调度器，共 48 窗','COMPLETED 0:0'],['120304','母控启动两窗','COMPLETED 0:0'],['120313','真实参数六窗 + 七模型控制计数','COMPLETED 0:0']],[70,335,102])
    p('均在旧服务器 node7 运行，12 核/任务、UNLIMITED；失败尝试及修复保留于交接，不把提交或部分后处理成功当成完整验收。',small)
    story.append(PageBreak());p('方法与避免重复计量',title)
    for h,t in [
      ('1. 母控核心','从冻结 FST 读取真实参数，综合网表与启动、运行样本配对。全窗功耗参考范围包含两启动窗和六运行窗；替换旧核心项，不再额外累加启动窗能量。状态驻留比例仍待校准。'),
      ('2. 局控外壳与分发','私有 RTL 副本切开 PM 和 scope_fetch 的 68 个接口端点，保留外壳逻辑；四站点路由参数从真实 FST 读取。48 窗全部边界标注，假设四外壳和四调度器全窗开钟；模型特有路由寄存表尚未逐一综合。'),
      ('3. 取指与交换机','静态遍历冻结控制页，核验 SHA/CRC、21 窗页数和 CALL 次数。每条 compact 指令一次 128-bit 控制 PM 读；成功 CALL 和返回各四 flit。每模型取指次数和 flit 数可复算，未计取消/重试。512-bit 是数据 SRAM 位宽。'),
      ('4. PM 宏和活跃差值','PM 使用既有四宏每次运行读的条件时钟弧成本，约 4.797 pJ/读，不重复加 OpenSTA 内部功耗。交换机采用 19 个窗内/20 个含起点握手事件的敏感性，约 0.178 - 0.288 pJ/flit，仅加活跃差值。四局控/调度样本 12.194 - 13.667 mW。'),
      ('5. 算术和代理','沿用 v3 真实输入的 RMS/softmax/RoPE 标定；apply/RoPE 内含 E32，不重复相加。GELU、GDN/Mamba、EXP/Softplus 等仍是明确的运算级成本代理，浮点迁移系数 0.5 - 2 倍。'),
      ('6. 证据边界','六模型直接绑定原计划 SHA；Qwen3 绑定原始已验收 pilot，并比较除位置相关计划 SHA 外的完整结果。当前 Qwen3 探针计划不在旧服务器，不能称其计划文件逐字节相同。')]:
        p(h,heading);p(t)
    story.append(PageBreak());p('第 2 步 Decode：两类估算',title)
    rows=[['模型','片上 mJ/token','片上 + DDR mJ/token','较 v3 新增 mJ/token']]
    for m,d in records.items():
        w=d['windows']['decode'];rows.append([NAMES[m],fmt(w['estimated_on_chip']['energy_mj_per_token']),fmt(w['estimated_on_chip_plus_ddr']['energy_mj_per_token']),fmt(w['control_net_increment']['energy_mj_per_token'])])
    table(rows,[95,135,142,135]);p(EXCLUDED,small)
    p('每模型后续三页依次给出三窗主值/控制项、底座分项、算术项与代理。DDR 只加入片上 + DDR；读 DMA 动态代理在单独场景中，未混入默认小计。')
    for m,d in records.items():
        story.append(PageBreak());p(NAMES[m],title);p(meta[m]['configuration']);p(meta[m]['implementation'],small)
        rows=[['窗口','片上 mJ/token','片上 + DDR mJ/token','片上 W','片上 + DDR W']]
        for name,w in d['windows'].items():rows.append([WINDOWS[name],fmt(w['estimated_on_chip']['energy_mj_per_token']),fmt(w['estimated_on_chip_plus_ddr']['energy_mj_per_token']),fmt(w['estimated_on_chip']['average_power_w']),fmt(w['estimated_on_chip_plus_ddr']['average_power_w'])])
        table(rows,[65,130,138,87,87]);p('控制分项（mJ/token）',heading)
        rows=[['新增/替换项','短 Prefill','首 Decode','第 2 步 Decode']]
        for key,label in CONTROL.items():rows.append([label]+[cfmt(d['windows'][n]['control_components'][key]['energy_mj_per_token']) for n in WINDOWS])
        rows.append(['减去旧母控核心']+[fmt(d['windows'][n]['replaced_native_mother_core']['energy_mj_per_token']) for n in WINDOWS])
        rows.append(['相对 v3 净增量']+[fmt(d['windows'][n]['control_net_increment']['energy_mj_per_token']) for n in WINDOWS])
        table(rows,[192,105,105,105]);p(EXCLUDED,small)
        c=d['windows']['decode']['control_counts'];p('本 Decode 窗：母控取指 %d 次；成功报文 flit %d；四站点 CALL %s。'%(c['instructions'],c['control_packet_flits'],c['calls_by_site']),small)
        story.append(PageBreak());p(NAMES[m]+'：底座分项',title)
        baseline=json.loads((HERE/(m+'_tlm_power_v2_no_wire.json')).read_bytes());rows=[['底座项（mJ/token）','短 Prefill','首 Decode','第 2 步 Decode']]
        for label,keys in COMPONENTS.items():
            row=[label]
            for name in WINDOWS:
                c=dict(baseline['windows'][name]['components'])
                c['native_mother_core_reference_1x']=d['windows'][name]['control_components']['native_mother_core_actual_parameter_reference']
                row.append(fmt([sum(c[k]['energy_mj_per_token'][e] for k in keys if k in c) for e in (0,1)]))
            rows.append(row)
        for key,label in CONTROL.items():
            if key.startswith('native_mother'):continue
            rows.append([label]+[cfmt(d['windows'][n]['control_components'][key]['energy_mj_per_token']) for n in WINDOWS])
        rows.append(['底座片上小计（含控制）']+[fmt([d['windows'][n]['previous_on_chip']['energy_mj_per_token'][e]+d['windows'][n]['control_net_increment']['energy_mj_per_token'][e] for e in (0,1)]) for n in WINDOWS])
        table(rows,[192,105,105,105]);p('底座已替换母控参数并加入三项控制增量；加下一页算术项得到主值。DDR 只计一次。',small);p(EXCLUDED,small)
        story.append(PageBreak());p(NAMES[m]+'：算术与代理',title)
        w=d['windows']['decode'];rows=[['第 2 步 Decode 算术项','mJ/token','依据']]
        for k,v in w['arithmetic_components'].items():
            if v['energy_mj_per_token'][1]==0:continue
            rows.append([LABELS[k],fmt(v['energy_mj_per_token']),'假设场景' if 'sensitivity' in k else '运算级代理' if k.startswith('proxy_') else '真实输入标定迁移'])
        rows.append(['算术小计',fmt(w['arithmetic_increment']['energy_mj_per_token']),'沿用 v3']);table(rows,[225,160,122])
        p('三窗算术小计（mJ/token）：'+ '；'.join(WINDOWS[n]+' '+fmt(d['windows'][n]['arithmetic_increment']['energy_mj_per_token']) for n in WINDOWS),small)
        p('读 DMA 动态独立情景',heading);rows=[['每拍成本假设','片上 mJ/token','片上 + DDR mJ/token']]
        for label,s in w['read_dma_sensitivity'].items():rows.append([{'half_write_cost':'写侧的 0.5 倍','same_write_cost':'写侧的 1 倍','twice_write_cost':'写侧的 2 倍'}[label],fmt(s['estimated_on_chip']['energy_mj_per_token']),fmt(s['estimated_on_chip_plus_ddr']['energy_mj_per_token'])])
        table(rows,[150,175,182]);p(EXCLUDED,small)
    story.append(PageBreak());p('复算、证据与剩余工作',title)
    p('复算：seven_model_control_estimate.py；独立检查：verify_control_estimate.py；报告：build_energy_report.py；所有入口在 work/Melodydt/280。原 v3 输入和索引保留，可比较控制补项前后差值。')
    p('还需完成：模型特有局控路由/参数、母控核心外控制包装及报文桥的匹配标定；实际门控/状态驻留；读 DMA 实测替换代理；匹配特殊算子 RTL 与数值回归；E32 调度及 M 300 MHz 时序；全局时钟、互连、PHY/封装/板级范围。')
    p('本报告不要求布局布线才给出估算；今后若加入线网寄生，应单独生成物理口径。Issue 仍 in_progress，草稿 PR 未合并，审查人待指定。未配置聊天自动监测。')
    for m in MODELS:p(NAMES[m]+' v4 SHA-256: '+sha256((HERE/(m+'_tlm_power_v4_control.json')).read_bytes()).hexdigest(),small)
    def page(c,doc):
        c.setFont('CN',8);c.setFillColor(colors.HexColor('#526875'));c.drawString(44,25,'LLMHardwareDesign | v4 控制补项 | 2026-11-18');c.drawRightString(A4[0]-44,25,str(doc.page))
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    SimpleDocTemplate(str(output),pagesize=A4,leftMargin=44,rightMargin=44,topMargin=45,bottomMargin=44,
       title='七模型能耗评估 v4：控制补项与参数纠正',author='Melodydt').build(story,onFirstPage=page,onLaterPages=page)
    print('CONTROL_REPORT_WRITTEN',output)


if __name__=='__main__':main()
