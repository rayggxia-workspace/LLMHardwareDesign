"""Render the rolling #280 power evaluation report from its result index."""

import argparse
from hashlib import sha256
from html import escape
import json
from math import isclose
from pathlib import Path

from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


REPO = "https://github.com/rayggxia-workspace/LLMHardwareDesign"
WINDOWS = {"prefill": "短 Prefill", "first_token": "首 Decode token", "decode": "第2步 Decode"}
COMPONENTS = {
    "DDR 芯片": ("ddr_devices",),
    "M 三路（FFN + 普通投影）": ("m_clocked_idle_3x", "m_busy_increment", "m_ordinary_projection_increment"),
    "数据 SRAM 四站点": ("s_p_clocked_idle_4x", "s_p_access_increment"),
    "母控 PM 四宏": ("mother_pm_clocked_idle_4_macros", "mother_pm_page_install_and_readback_increment"),
    "九目标母控核心": ("native_mother_core_reference_1x",),
    "局控 PM（驻留/启动/读取）": ("lc_pm_loaded_quiet_4x", "lc_pm_boot_crc_increment", "lc_pm_runtime_read_increment"),
    "局控描述符（驻留/活动）": ("lc_descriptor_fetch_quiet_4x", "lc_descriptor_fetch_active_increment"),
    "G32 空闲及活跃增量": ("g32_down_idle_1x", "g32_active_increment"),
    "U ADD2 链（驻留/活动）": ("u_add2_logic_active_increment", "u_add_chain_clocked_idle_1x"),
    "局部交换机静默": ("cohort_switch_idle_1x",),
    "写 DMA（驻留/活动）": ("write_dma_active_increment", "write_dma_clocked_idle_1x"),
    "PM 传输桥（驻留/装载）": ("pm_transport_clocked_idle_1x", "pm_transport_install_increment"),
}
INK = colors.HexColor("#172A3C")
MUTED = colors.HexColor("#43566A")
ACCENT = colors.HexColor("#006D68")
RULE = colors.HexColor("#D8E4EC")
PAPER = colors.HexColor("#F1F6F9")
WIDTH = A4[0] - 100


def make_styles():
    body = ParagraphStyle("body", fontName="CN", fontSize=10.5, leading=16, textColor=INK,
                          wordWrap="CJK", spaceAfter=7)
    return {
        "body": body,
        "title": ParagraphStyle("title", parent=body, fontName="CNBold", fontSize=29, leading=36, spaceAfter=10),
        "section": ParagraphStyle("section", parent=body, fontName="CNBold", fontSize=15, leading=21,
                                  spaceBefore=12, spaceAfter=5),
        "eyebrow": ParagraphStyle("eyebrow", parent=body, fontName="CNBold", fontSize=10, textColor=ACCENT,
                                  spaceAfter=5),
        "note": ParagraphStyle("note", parent=body, fontSize=9, leading=13, textColor=MUTED),
        "table": ParagraphStyle("table", parent=body, fontSize=9.5, leading=12.6, spaceAfter=0),
        "value": ParagraphStyle("value", parent=body, fontSize=9.5, leading=12.6, spaceAfter=0, alignment=TA_RIGHT),
        "tablehead": ParagraphStyle("tablehead", parent=body, fontName="CNBold", fontSize=9.2, leading=13,
                                    textColor=colors.white, spaceAfter=0),
    }


def add(story, styles, text, style="body"):
    story.append(Paragraph(escape(text.replace('\u2013', '-').replace('\u2014', '-').replace('\u2011', '-')), styles[style]))


def link(story, styles, label, url):
    story.append(Paragraph(f'<link href="{escape(url, quote=True)}" color="#006D68">{escape(label)}</link>', styles["note"]))


def table(story, styles, columns, rows, ratios, numeric=True):
    cells = [[Paragraph(escape(label).replace("\n", "<br/>"), styles["tablehead"]) for label in columns]]
    for row in rows:
        cells.append([Paragraph(escape(str(value)), styles["value" if numeric and i > 0 else "table"])
                      for i, value in enumerate(row)])
    grid = Table(cells, colWidths=[WIDTH * ratio for ratio in ratios], repeatRows=1, hAlign="LEFT")
    grid.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PAPER]),
        ("LINEBELOW", (0, -1), (-1, -1), 0.6, RULE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.extend([grid, Spacer(1, 7)])


def fmt(bounds, digits=3):
    lo, hi = (f"{value:.{digits}f}" for value in bounds)
    return lo if lo == hi else f"{lo} - {hi}"


def load_result(model, directory):
    raw = (directory / model["result"]).read_bytes()
    if sha256(raw).hexdigest() != model["result_sha256"]:
        raise ValueError(f"result hash mismatch for {model['name']}")
    result = json.loads(raw)
    for window in WINDOWS:
        row = result["windows"][window]
        if (row["elapsed_ps"] <= 0 or row["tokens"] <= 0
                or not isclose(row["tokens_per_second"], row["tokens"] * 1e12 / row["elapsed_ps"], rel_tol=1e-9)):
            raise ValueError(f"window time or token count mismatch for {model['name']}: {window}")
        for metric in ("energy_nj_per_window", "energy_mj_per_token", "average_power_w"):
            for chip, ddr, combined in zip(row["covered_on_chip_subtotal"][metric],
                                            row["components"]["ddr_devices"][metric],
                                            row["covered_subtotal"][metric]):
                if not isclose(chip + ddr, combined, rel_tol=1e-12):
                    raise ValueError(f"on-chip/DDR accounting mismatch: {model['name']} {window}")
    return result


def overview(story, styles, index):
    add(story, styles, f"LLMHardwareDesign  /  Issue #280  /  v{index['revision']}", "eyebrow")
    add(story, styles, "七模型功耗与能耗评估", "title")
    add(story, styles, f"报告更新于 {index['updated']}（北京时间）  |  负责人 {index['owner']}", "note")
    if index.get('wire_parasitics_loaded') is False:
        add(story, styles, "本版统一不加载布局布线寄生。复用网络仍保留已有单元、缓冲器和引脚电容；新母控仅综合映射。新增缺项与去寄生影响分开核算。", "note")
    add(story, styles, "基准与采样窗口", "section")
    add(story, styles, "以 #274 / PR #275 的模型短程回放为基础，继承 PR #260 的两步 Decode 和短 Prefill 结构。使用 300 MHz 分项标定、512-bit 数据 SRAM 和代表性真实历史。逐模型记录 FFN 部署、变更的调度与物理范围。")
    add(story, styles, "发布短 Prefill、开始到首个 Decode 输出、两次 Decode 退休间三窗的实际时长、tok/s、平均 W 和 mJ/token。Prefill 按输入 token 归一化，Decode 按输出 token 归一化。第2步是代表窗口，不是长序列稳态统计。")
    add(story, styles, "分项积分", "section")
    add(story, styles, "窗口能量 = 各分项开钟基线功耗 × 驻留时间 + 各事件数 × 单次活动增量。已有配对标定先扣匹配的静默基线。M 等采用忙/闲时间积分，SRAM 和 DMA 采用对账后的位宽及事务计数。DDR 芯片沿用双通道器件模型。")
    add(story, styles, "平均功耗 = 窗口能量 ÷ 窗口时间。每 token 能耗 = 窗口能量 ÷ token 数。共享模块、局部时钟和漏电仅计一次。代理值随条件标注，缺项保留待标定。")
    add(story, styles, "统一报告两类：①片上已覆盖小计，含已标定的计算、SRAM、PM、局控与片上 DMA 项；②片上已覆盖 + DDR 器件能耗。后者在前者上只加 DDR 器件项；DDR PHY、板级 I/O 等未覆盖项不混入。两类分别报告 W 和 mJ/token。", "note")
    add(story, styles, "跨模型扩测复用已标定叶块的系数，并使用各模型重新观测的事件数与时间。新增模型结果属于迁移估算；特殊激活、循环计算等缺少匹配标定的工作单列，不能将已覆盖小计当作完整模型总能耗。", "note")
    add(story, styles, "报告覆盖", "section")
    table(story, styles, ("模型", "能耗证据"), [(m["name"], m["status"]) for m in index["models"]],
          (0.46, 0.54), numeric=False)
    link(story, styles, "七模型基准源版本 · Issue #274 / PR #275", f"{REPO}/blob/{index['benchmark_commit']}/work/Melodydt/274/README.md")
    link(story, styles, "评估任务 · Issue #280", f"{REPO}/issues/280")
    link(story, styles, "交付审查 · PR #281", f"{REPO}/pull/281")


def result_page(story, styles, model, result):
    add(story, styles, "模型结果  /  " + model["status"], "eyebrow")
    add(story, styles, model["name"], "title")
    add(story, styles, model["configuration"])
    add(story, styles, model["implementation"], "note")
    add(story, styles, "已覆盖能耗与平均功耗", "section")
    rows = []
    for window, name in WINDOWS.items():
        row = result["windows"][window]
        chip, combined = row["covered_on_chip_subtotal"], row["covered_subtotal"]
        rows.append((name.replace("首 Decode token", "首 Decode"), f'{row["elapsed_ps"] / 1e9:.3f}', f'{row["tokens_per_second"]:.3f}',
                     fmt(chip["energy_mj_per_token"]), fmt(chip["average_power_w"], 4), fmt(combined["energy_mj_per_token"]),
                     fmt(combined["average_power_w"], 4)))
    table(story, styles, ("窗口", "时长 ms", "tok/s", "片上覆盖\nmJ/token", "片上覆盖\n平均 W", "片上+DDR\nmJ/token", "片上+DDR\n平均 W"),
          rows, (0.16, 0.11, 0.10, 0.18, 0.12, 0.20, 0.13))
    add(story, styles, "短 Prefill 为 2 个输入 token，两个 Decode 窗各为 1 个输出 token。已覆盖区间来自标定样本端点，拓扑和驻留不确定性另列。", "note")
    add(story, styles, "分项归属  /  mJ/token", "section")
    results = [result["windows"][key]["components"] for key in WINDOWS]
    groups = dict(COMPONENTS)
    known = {key for keys in groups.values() for key in keys}
    extra = sorted(set().union(*results) - known)
    groups.update({key: (key,) for key in extra})
    rows = []
    for label, keys in groups.items():
        values = []
        for components in results:
            available = [components[k]["energy_mj_per_token"] for k in keys if k in components]
            values.append(fmt([sum(items) for items in zip(*available)], 6)
                          if available else "待标定")
        if any(value != "待标定" for value in values):
            rows.append((label, *values))
    table(story, styles, ("分项", *WINDOWS.values()), rows, (0.37, 0.21, 0.21, 0.21))


def additions_page(story, styles, records):
    add(story, styles, "无布线寄生 / 新增覆盖", "eyebrow")
    add(story, styles, "本版补入了什么", "title")
    add(story, styles, "新增普通投影 M 活跃项；写 DMA、U ADD2 链及 PM 传输桥的开钟驻留；PM 传输/局控启动 CRC；局控 PM 运行读取和描述符取指活动。九目标母控完成匹配综合与六窗活动核验，参考功耗已加入。")
    add(story, styles, "下表取第2步 Decode，单位 mJ/token。旧版含线网寄生，本版重新计算全部已有分项，因此总数下降不能解读为新增模块降低能耗。")
    rows=[]
    for model, result in records:
        row=result['windows']['decode']
        old=row['prior_with_wire_covered_on_chip_subtotal']['energy_mj_per_token']
        added=row['newly_included_subtotal']['energy_mj_per_token']
        new=row['covered_on_chip_subtotal']['energy_mj_per_token']
        same=[v-added[i] for i,v in enumerate(new)]
        rows.append((model['name'],fmt(old),fmt(same),fmt(added),fmt(new)))
    table(story,styles,("模型","旧片上小计\n含线网 RC","原分项\n去线网 RC","本次新增\n片上分项","新片上\n覆盖小计"),rows,(.24,.19,.19,.19,.19))
    add(story,styles,"计数与归属", "section")
    add(story,styles,"普通投影按各模型实际 M 忙区间计入，采用 C639 活跃减静默系数。局控每次顶层服务按 20 个元数据字加 3 次指令字读取、一次 128 B 描述符抓取估算；MoE 等服务内部算术不重复算作顶层 CALL。PM 启动只在实际安装的首窗计入。")
    add(story,styles,"驻留仍采用条件部署：三 M、四数据 SRAM、四局控 PM/取指，以及共享的 G32、交换机、写侧、U 链、PM 传输桥和母控。真实实例数、门控与各模型特有部署仍待验证。", "note")
    add(story,styles,"仍不能填成零的部分", "section")
    add(story,styles,"读 DMA 实测功耗；母控运行取指与启动；局控外壳和分发；交换机实际流量；RMS、softmax、RoPE、缩放及特殊 GELU/GDN/Mamba2/router 算术；尚未综合的全局时钟/互连单元；DDR PHY 和板级 I/O。布线寄生是本版主动排除项，与这些未覆盖硬件分开。", "note")


def comparison_page(story, styles, records, include_ddr):
    key = "covered_subtotal" if include_ddr else "covered_on_chip_subtotal"
    add(story, styles, "同口径汇总  /  类型二" if include_ddr else "同口径汇总  /  类型一", "eyebrow")
    add(story, styles, "片上 + DDR 器件" if include_ddr else "片上已覆盖能耗", "title")
    add(story, styles, "下表保留各模型的实测 TLM 窗口与分项标定范围，不加入读 DMA 动态代理。短 Prefill 按输入 token，Decode 按输出 token 归一化。单位均为 mJ/token，最后一列为两次退休间窗口的平均 W。")
    rows = []
    for model, result in records:
        windows = result["windows"]
        energy = [fmt(windows[window][key]["energy_mj_per_token"]) for window in WINDOWS]
        rows.append((model["name"], *energy, fmt(windows["decode"][key]["average_power_w"], 4)))
    table(story, styles, ("模型", "短 Prefill\nmJ/token", "首 Decode\nmJ/token", "第2步 Decode\nmJ/token", "第2步 Decode\n平均 W"),
          rows, (0.25, 0.185, 0.185, 0.185, 0.195))
    add(story, styles, "如何使用这张表", "section")
    events = "DDR、SRAM、PM、FFN 和残差" if include_ddr else "SRAM、PM、FFN 和残差等片上"
    add(story, styles, "驻留功耗按共用条件配置和模型自己的实际时间积分，因此更长的执行时间会产生更高的每 token 驻留能耗。动态项来自各模型重新观测的" + events + "事件。")
    add(story, styles, "特殊算术缺项随模型不同：GELU、GDN、Mamba2、router 等尚未全部门级标定。不能据此表排列完整芯片的能效优劣，也不能把标定样本端点当作整体误差范围。各模型的专项实现、缺项和读 DMA 敏感性见后页。")
    add(story, styles, "旧版 M 的 300 MHz 时序未闭合；本报告沿用用户选择的固定 TLM 时间参考路线。综合后补齐活动标定时继续更新同名报告。", "note")


def dma_proxy(story, styles, result):
    terms = [result["windows"][window] for window in WINDOWS]
    if not all(row.get("read_dma_dynamic_sensitivity") for row in terms):
        return
    add(story, styles, "读 DMA 动态敏感性", "section")
    if all("write_dma_transferred_pj_per_64b" in row for row in terms):
        add(story, styles, "复用 Qwen3 真实写载荷标定的 64 B 单价范围，以其中点作为读侧动态代理，并对该单价取 0.5 和 2 倍。本模型的读写事务已重测，逐位载荷尚未重新门级标定。DDR 芯片另计；读 DMA 常驻空闲和漏电待补。")
    else:
        add(story, styles, "以同窗口写侧 64 B 实测单价中点作为读侧动态代理，并对该单价取 0.5 和 2 倍。DDR 芯片已单独计入，读 DMA 的常驻空闲及漏电仍待标定。倍数只描述所选情景。")
    rows = []
    sensitivity_rows = []
    for name, row in zip(WINDOWS.values(), terms):
        scenarios = row["read_dma_dynamic_sensitivity"]
        midpoint = scenarios["same_write_cost"]
        subtotal = midpoint["subtotal_with_read_dma_active_proxy"]
        low = scenarios["half_write_cost"]["subtotal_with_read_dma_active_proxy"]["energy_mj_per_token"][0]
        high = scenarios["twice_write_cost"]["subtotal_with_read_dma_active_proxy"]["energy_mj_per_token"][1]
        ddr = row["components"]["ddr_devices"]["energy_mj_per_token"]
        chip = [total - memory for total, memory in zip(subtotal["energy_mj_per_token"], ddr)]
        sensitivity_rows.append((name.replace("首 Decode token", "首 Decode"), fmt([low - ddr[0], high - ddr[1]]), fmt([low, high])))
        rows.append((name.replace("首 Decode token", "首 Decode"), f'{midpoint["assumed_read_pj_per_64b"]:.3f}',
                     fmt(midpoint["read_dma_active_proxy"]["energy_mj_per_token"]),
                     fmt(chip), fmt(subtotal["energy_mj_per_token"])))
    table(story, styles, ("窗口", "同写单价\npJ / 64 B", "动态增量\nmJ/token", "片上加代理\nmJ/token", "片上 + DDR\n加代理 mJ/token"),
          rows, (0.19, 0.15, 0.17, 0.24, 0.25))
    add(story, styles, "0.5-2 倍读侧动态情景仍分别保留两类范围；这是所选代理的敏感性，不是整体误差界。", "note")
    table(story, styles, ("窗口", "片上加代理\n0.5-2 倍 mJ/token", "片上 + DDR 加代理\n0.5-2 倍 mJ/token"),
          sensitivity_rows, (0.28, 0.36, 0.36))
    if all("ddr_transport_beats_64b" in row for row in terms):
        reads = " / ".join(f'{row["ddr_transport_beats_64b"]["read"]:,}' for row in terms)
        writes = " / ".join(f'{row["ddr_transport_beats_64b"]["write"]:,}' for row in terms)
        add(story, styles, f"三窗对账的 64 B 事务数，读 {reads}，写 {writes}。", "note")
    sensitivity = " / ".join(f'{row["remaining_100mw_residency_mj_per_token"]:.3f}' for row in terms)
    add(story, styles, f"每增加 100 mW 未计入的整窗常驻功耗，三窗分别增加 {sensitivity} mJ/token。", "note")


def next_steps(story, styles, index, records):
    add(story, styles, "综合后直接估功耗", "section")
    add(story, styles, "等读 DMA 技术映射网表输出后，在 OpenSTA 载入网表、Nangate45 TT Liberty 和 300 MHz SDC，读入端口匹配且时标转换后的 C639 VCD。记录活动标注率、传播活动、动态和漏电。无 SPEF 时以单元及引脚负载估算，可在布局布线完成前运行。")
    add(story, styles, "配对静默、正常、背压和读写并发样本后，将读侧空闲及动态按相同窗口回填。阶段包装和内部共享 fabric 只计一次。补齐母控运行取指/启动、局控外壳、其余控制与计算，再验证各模型实例数、门控及全局时钟单元。DDR PHY 和板级 I/O 单列；本版不要求布局布线寄生。")
    add(story, styles, "版本维护与复现", "section")
    add(story, styles, "每完成一个模型或取得更强的标定证据，核验时窗、token、FP32 和事务对账，登记结果、输入和工具版本及 SHA-256，重建同名 PDF。不同覆盖范围、活动假设和各模型专项优化随各自结果记录。")
    add(story, styles, "七模型的原回放继承同历史 FP32 验收。新分项使用服务器重算的无寄生标定及验收的 TLM 时间/事件，本地进行分项守恒和双口径复算；不代表重新运行七模型 FP32 或整模型门级仿真。原始活动和网表留在授权服务器，仓库保留小型回执和复算入口。", "note")
    for model, _ in records:
        commit = model.get("source_commit", index["source_commit"])
        for item in model["sources"]:
            link(story, styles, item["label"], f'{REPO}/blob/{commit}/{item["path"]}')
    for item in index.get('sources', []):
        link(story, styles, item['label'], f'{REPO}/blob/{index["source_commit"]}/{item["path"]}')
    add(story, styles, f'评估证据版本 {index["source_commit"]}', "note")


def draw_page(canvas, document):
    width, height = A4
    canvas.setStrokeColor(ACCENT)
    canvas.setLineWidth(1.4)
    canvas.line(44, height - 44, width - 44, height - 44)
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.6)
    canvas.line(44, 41, width - 44, 41)
    canvas.setFont("CN", 8.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(44, 26, "LLMHardwareDesign  /  Issue #280")
    canvas.drawRightString(width - 44, 26, f"{document.page}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=Path(__file__).with_name("energy_report_models.json"))
    parser.add_argument("--output", type=Path, default=Path("output/pdf/seven-model-energy-evaluation.pdf"))
    parser.add_argument("--regular-font", type=Path, default=Path("C:/Windows/Fonts/Deng.ttf"))
    parser.add_argument("--bold-font", type=Path, default=Path("C:/Windows/Fonts/Dengb.ttf"))
    args = parser.parse_args()
    index = json.loads(args.index.read_bytes())
    records = [(model, load_result(model, args.index.parent)) for model in index["models"] if "result" in model]
    rl_config.invariant = 1
    pdfmetrics.registerFont(TTFont("CN", str(args.regular_font)))
    pdfmetrics.registerFont(TTFont("CNBold", str(args.bold_font)))
    styles = make_styles()
    story = []
    overview(story, styles, index)
    if len(records) > 1:
        for include_ddr in (False, True):
            story.append(PageBreak())
            comparison_page(story, styles, records, include_ddr)
    if records and all('newly_included_subtotal' in r['windows']['decode'] for _,r in records):
        story.append(PageBreak())
        additions_page(story,styles,records)
    for model, result in records:
        story.append(PageBreak())
        result_page(story, styles, model, result)
        if all(row.get("read_dma_dynamic_sensitivity") for row in result["windows"].values()):
            story.append(PageBreak())
            add(story, styles, "估算边界与后续标定", "eyebrow")
            add(story, styles, model["name"], "title")
            dma_proxy(story, styles, result)
            if model.get("coverage"):
                add(story, styles, "本模型的迁移假设与缺项", "section")
                for paragraph in model["coverage"]:
                    add(story, styles, paragraph, "note")
    if len(records) > 1 or not records or not all(row.get("read_dma_dynamic_sensitivity") for row in records[-1][1]["windows"].values()):
        story.append(PageBreak())
        add(story, styles, "后续步骤与证据", "title")
    next_steps(story, styles, index, records)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(str(args.output), pagesize=A4, leftMargin=44, rightMargin=44, topMargin=58,
                                 bottomMargin=48, title="七模型功耗与能耗评估", author=index["owner"])
    document.build(story, onFirstPage=draw_page, onLaterPages=draw_page)


if __name__ == "__main__":
    main()
