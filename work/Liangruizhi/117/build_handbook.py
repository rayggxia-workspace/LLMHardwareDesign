"""Offline: build the evidence directory, task ledger and complete Markdown edition."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOC = ROOT / "docs/research-handbook"
WORK = Path(__file__).resolve().parent

# Execution summaries, deliberately independent of GitHub's workflow labels.
SUMMARIES = {
    1: ("文档接入", "导入项目定义、初期资料、来源和目录，建立可维护的项目入口。", "材料接入不能证明完整物理流程可复现。"),
    3: ("文档交付", "同步布线/线长/模块与接口报告及llaccel分析，保留参考资料边界。", "不把已有结果包当完整源工程或新实验。"),
    5: ("协作交付", "明确Issue、独立分支/目录、身份、个人进度、SHA和交接规则。", "PR上传与审查合并、登记和看板分别核验。"),
    7: ("工程已执行，含失败", "完成VECTOR及并行块分层试验、宏视图、PG接入和接口检查。", "VECTOR setup/cap及父层失败保留；多个报告各有版本，非最终底座。"),
    9: ("规则文档", "记录服务器目录、资源和作业命名规则并提供入口。", "规则存在不表示本次整理启动或检查服务器作业。"),
    11: ("抽象实验完成", "192例冻结互联搜索，32/96与44/96成功；小例穷举和电气/数值复核。", "搜索预算不同；合成连通不等于真实H2/时序。"),
    13: ("配对消融完成", "同master库存384例，扩接点44→71/96；保留cut证书和未知失败。", "不是工艺访问或芯片PPA；capacity无变化不等于永远无用。"),
    15: ("H1工程对照完成", "ACT/MXU拆分与合并完整物理/功能/RC证据；叶面积+0.412%、线+7.142%、via+2.974%。", "单small/typical且允许有源修复，不是普遍制造后改线证明。"),
    16: ("端点冻结完成", "三普通LEF、6785信号位与原始PORT/RECT/OBS完整库存、独立解析。", "几何矩形和中心不是合法via/access；底层版本缺项保留。"),
    19: ("接口核验完成", "ACT/MXU共3032信号位三视图及685bit既有连接合同。", "两处Liberty缺分号、四处PG方向差异；无完整arc/物理资格。"),
    21: ("结构/数学研究完成", "9配置案例、11340容量条件及流式/物化反例；MLA/MoE缩小数学核。", "不是9个真实权重模型，不把FP32账本缩放为INT8。"),
    23: ("真实模型参考完成", "Qwen3-0.6B固定权重，54调用、完整KV/fresh-prefix及错误状态负例。", "FP32短上下文与局部边界；无语言质量/目标性能结论。"),
    25: ("benchmark调研完成", "通用INT8功能、真实尺寸、容量/通信公式和模型/模块/数据集分层。", "不含新权重运行、质量、RTL或物理实测。"),
    27: ("状态服务研究完成", "3456固定bank/端口/连接配置、真实Qwen头参考、独立调度审计。", "假设服务；1RW位置收益4.51%/3.92%，不能继承到整数电路。"),
    29: ("端口RTL完成，综合受阻", "27配置、1872程序及54压力测试；有限FIFO/反压/逐拍witness。", "算术为延迟代理；原型综合超时，不称完整attention或SRAM宏实现。"),
    31: ("有限H2切片完成", "同功能冻结资源，仅M8–M10/V8/V9重布；DRC/PG/RC/完整分层STA通过。", "约92.5%父层线已预埋，无第二计算图，不是通用共同底座。"),
    32: ("GPU模型及修订执行", "Qwen2.5/Qwen3.5 FP16参考、真实INT8矩阵、分组敏感性和规范辅助长连续对照。", "早期OOM/状态失败保留；FP32辅助存在，非全整数模型。"),
    33: ("整数合同/小核完成", "W8A8/INT32、RQ RTL1028例、LUT/小norm/小递推、真实切片与4608划分点。", "原参考RTL规范不完整；质量和全模型硬件未通过。"),
    37: ("模型筛选完成", "先比较GQA/窗口/递推/MLA/MoE和训练/权重差异，再冻结最小协议。", "历史配置访问缺项以后续实际采集补齐，不倒改成早期已跑。"),
    39: ("局部整数诊断完成", "Qwen真实head的24块scale/概率候选、89280 oracle值、bias与错误scale反例。", "当前张量拟合含前视，尚非因果全GQA/质量结论。"),
    41: ("分析候选完成", "给出M/V/A/R/S/D计算/状态/接口/预连线和决策型最小实验。", "候选不是目标电路或制造边界验收。"),
    42: ("组合锥方法完成", "同两门底座两目标、冻结/连通/逻辑参数化重放，15测试与原证据绑定。", "小组合片段，无完整状态核心/DRC/LVS/STA。"),
    43: ("五项目资源调研完成", "区分板上/仿真/规划与INT8/FP32/W4/BF16，形成数量/容量/带宽约束。", "B数及PE数不能直接定完整模型Block数。"),
    47: ("因果GQA合同完成", "独立校准、全2Q/1KV共享变换、静态KV和未来扰动/版本测试。", "当前scale编译有浮点；局部约1.8%误差不是质量验收。"),
    48: ("估计器交付完成", "严格≤4B W8A8/INT32输入、31测试、四例双轮，unknown和通信/容量分开。", "仅下界/显式假设，不自动证明模型可部署或时延。"),
    51: ("RQ服务对照完成", "384组织/192位置对，同库存双策略包络；decode物理包节省为0。", "近M最优包络约0.5657%，未校准完整算术/物理。"),
    53: ("CPU迁移完成", "Qwen3 FP32/BF16×8/16/32线程、双轮参考及计时。", "BF16部分线程失败，CPU时间不替代GPU/目标Block。"),
    55: ("完整集成部分完成", "原完整顶层、四宏/状态归属、open观察器及llaccel补测已有证据。", "迁线异网接触失败；共同底座/M8/两案例定制未完成。"),
    56: ("Llama跨模型完成", "完整4Q/1KV和K8192/16输出，独立整数、早RQ反例、有限端口。", "静态down近全零；不是全FFN或全模型质量。"),
    59: ("校准/粒度比较完成", "Llama24候选/144数值条件、宽归约、元数据与1152服务配置。", "最佳5.39%仍未过原5%探索门；权重相关界不覆盖全层。"),
    61: ("四模型批次执行完成", "Qwen2.5/Qwen3.5/Gemma主测及Phi封存；420线性/56注意力条件。", "部分格式/饱和失败保留；CPU FP32参考、非全整数/新GPU测量。"),
    63: ("软件/研究交付完成", "适配、生命周期、真实pin导入；223测试、10重放和通信搜索强基线。", "合成资源研究，真实M8/冻结底座C层blocked。"),
    64: ("决策分叉完成", "输出格式1080条件、整数注意力56条件、576服务图及Block v2。", "局部改善不升级旧质量；M+A合宏仍未物理证明。"),
    66: ("消费者/连续整数研究完成", "完整H2560 down-residual-norm-next切口及Qwen双head连续R/conv。", "旧长窗饱和保留，部分生产链FP桥仍在；范围策略由68补。"),
    68: ("范围及同资源服务完成", "static/guard/adaptive对照、完整checkpoint、448服务日历及独立接收。", "重标改变函数；宽算术假设瓶颈不等于物理宏最优。"),
    70: ("架构扩展最小集执行", "新增Granite/Falcon参考、真实切口和COPY/端口对照。", "Granite chunk失败，Falcon早期浮点更新/sat不升级整数。"),
    72: ("数值闭环与服务完成", "Granite路由精度/证书；Falcon32head完整整数分支/恢复/输出分组。", "Attention/MLP切口外；物理归属微小条件差不定稿。"),
    74: ("完整MoE切口完成", "两层8条件全部专家/merge/残差/nextnorm；Falcon分组同函数M/V比较。", "Granite质量局部误差仍在，offline末8行不冒充新cached调度。"),
    76: ("有限merge服务完成", "24配置及byte/ROM微核校准；fullH merge峰14224B可驻V。", "公共microframe过慢，尚非完整wide FSM或PPA。"),
    80: ("宽控制RTL完成", "895命令×四条件、实际取指/CALL/RMW/ROM，LOCAL周期少约44%。", "任务分布非模型频率，512B框架与后续norm不是同库存。"),
    82: ("norm/真实M电路完成", "三硬件profile、174命令，完整K512/H1536消费者逐码。", "最快norm完整链只少2.166%，面积增加，未物理定稿。"),
    84: ("缓存/共享电路完成", "同16KiB/端口A缓存与一个S32，84命令及端口反转反例。", "静态编译变体，零竞争不代表并发零成本。"),
    85: ("运行时/恢复完成", "单核cache_mode锁存、显式cmd握手、60完整输出及中止恢复。", "epoch终止缺陷后来由92修复；独立fabric/CDC未验。"),
    86: ("选定门级完成，STA失败", "四84网表双等待完整门级通过；全DFF/IO受限STA暴露大量违例。", "零延迟门级非形式等价，诊断周期不是合格Fmax。"),
    88: ("受限电气修复完成", "四变体缓冲/tie/驱动/hold成本及精确8条门级通过。", "无真实线RC/CTS；历史native电气摘要需按98完整表提升口径。"),
    91: ("结构合同完成", "H2560 X驻留/gamma流式、frame/A容量与符号行证明。", "当轮无张量/RTL，实际实现由93完成。"),
    92: ("边界修复完成", "复现并修max generation排空与cfg/done假握手，10条门锥性质。", "一周期安全非完整活性/任意重排/门级注入证明。"),
    93: ("流式gamma RTL完成", "双等待各51完成记录，六Granite链及两Gemma完整H2560 norm。", "cost02修正beat字节；最终物理网表的完整门级另见98。"),
    97: ("V到M完整电路完成", "真实gate/up→SiLU/MID→整K量化→M/merge/residual/norm，selected gate通过。", "router/gate-up投影和通用V/整模型不在切口。"),
    98: ("物理阶段部分完成", "97精确研究物理及4×2正常门级accepted；93最终物理表通过。", "93完整门级接收在来源快照未完成，本次未查服务器新终态。"),
    99: ("Falcon单head RTL完成", "72连续、全head重标、readout/root发布及两checkpoint门级。", "不是32head完整分支或4096消费者RTL，不继承98物理。"),
    102: ("完整GQA切片完成", "79query双等待、完整8头QK到PV和版本恢复，selected gate通过。", "非online，无KV append/投影/RoPE/全模型。"),
    104: ("GDN双head RTL完成", "native32/portable12、S32宽lowering、共同root、恢复/边界及selected gate。", "输入生产/输出gatednorm切口外；引用参考优先级补丁须一并接收。"),
    106: ("三profile真共享完成", "M/A/Falcon共用同S/8S8/S32/SFU/link，7混合/27恢复双等待。", "最大6KiB环境sink未实现为下游硬件buffer，新top未物理。"),
    109: ("四profile真共享完成", "接GDN、完整2048B候选导出，13混合/44恢复及双路8命令gate。", "串行owner非模型端到端，新logic-only面积163901.220需独立物理。"),
    110: ("等价面积精化完成", "真实组合锥/FF归纳、24套回归/6门级；QK34/PV45少0.80921%面积。", "周期不变，无STA，未合入109。"),
    114: ("分析文档已合并", "YUZE-LU八模型能力/Block边界报告经PR115进入main。", "只验文档，不代批原实验PR或升级模型/物理资格。"),
    116: ("其他成员归档任务", "安排docs/model-analysis图册/分析归档，保留原成果与跳转。", "本任务不移动或覆盖其文件，实际本地/远端阶段以该Issue为准。"),
    117: ("本次完整教程交付", "逐模型、数值推理、具体划分、电路/物理/映射与完整证据总账。", "仅文档/来源核对，原实验未重跑；最终上传回执另见本任务交接。"),
}


def write(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def evidence_directory(manifest: dict) -> None:
    rows = manifest["sources"]
    text = [
        "# 10｜固定版本证据目录",
        "",
        "本章由source-index.json生成。S编号是正文引用，D编号是结果索引，T编号是Issue正文的时间快照。",
        "固定Git链接的40位commit给出本次读取版本；SHA-256绑定文件原字节。它们不表示本次重新执行原实验。",
        "",
        f"采集时间（UTC）：`{manifest['captured_at_utc']}`；主线基线：`{manifest['main_commit']}`。",
        "",
        "[机器可读清单](source-index.json)与[原文证据包](../../work/Liangruizhi/117/source-documents.zip)可离线核对。",
        f"证据包 {manifest['capsule']['bytes']:,} B，{manifest['capsule']['members']}成员，SHA-256 `{manifest['capsule']['sha256']}`。",
        "包内只有本次所读文档、结果索引和任务正文；无模型权重、封存Phi内容、原实验大张量、EDA库或凭据。",
        "",
        "## 1. 报告、候选方案与方法",
        "",
        "正文较早报告中的‘未完成’按当时范围阅读；后续修订另有来源。不要只读最早一份就否定后续已做工作。",
        "",
    ]
    for x in rows:
        if x["kind"] != "git-document":
            continue
        pr = x["pr"]
        text.extend([
            f'<a id="{x["id"]}"></a>',
            f"### {x['id'].upper()} · {x['path']}",
            "",
            f"来源：[PR{pr}](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/{pr})；[固定原文]({x['url']})。",
            f"文件所在commit：`{x['head']}`；原字节{x['bytes']:,} B；SHA-256 `{x['sha256']}`。",
            "运行代码版本请继续读原报告的source/binding；文件所在commit可能是后续交付提交。",
            "",
        ])
    text.extend(["## 2. 结果索引", "", "下列JSON给出数据/源码/完整包/精选范围。拿到索引不表示大文件已取得或有访问权限。", ""])
    for x in rows:
        if x["kind"] == "git-result-index":
            text.extend([
                f'<a id="{x["id"]}"></a>',
                f"- **{x['id'].upper()}**：[固定索引]({x['url']})；{x['bytes']:,} B；SHA-256 `{x['sha256']}`。",
                "",
            ])
    text.extend(["## 3. Issue快照", "", "Issue会继续更新，故不能把网页当前正文视为冻结Git文件。本包保存了采集时原正文，更新时间和SHA在JSON中。工作流状态见第11章，最后交付状态见Issue117/PR回执。", ""])
    for x in rows:
        if x["kind"] == "issue-body-capture":
            text.extend([
                f'<a id="{x["id"]}"></a>',
                f"- **T{x['issue']}**：[原Issue]({x['url']})；原更新时间`{x['updated_at']}`；{x['bytes']:,} B；正文SHA-256 `{x['sha256']}`。",
                "",
            ])
    text.extend([
        "## 4. 怎么理解这份清单",
        "",
        "Git blob标识使用Git对象算法，SHA-256用于本次原字节核对，两者用途不同。离线检查会从原字节重算Git blob，核清单、zip成员和声明来源；它不能仅靠哈希证明作者或源实验数学正确。",
        "",
        "若PR后来前进，先确定要复现本报告固定版本还是新版本。新结果可以增补，不覆盖旧快照和失败。大文件继续留授权位置，通过各实验索引接收。",
    ])
    write(DOC / "10-evidence-index.md", "\n".join(text))


def ledger(snapshot: dict, manifest: dict) -> None:
    assert {x["number"] for x in snapshot["issues"]} == set(SUMMARIES), "New task needs a reviewed summary"
    by_issue: dict[int, list[dict]] = {}
    for p in snapshot["pulls"]:
        for n in SUMMARIES:
            if p["branch"].startswith(f"task/{n}-"):
                by_issue.setdefault(n, []).append(p)
    lines = [
        "# 11｜全项目任务总账：执行成果与协作状态分别看",
        "",
        f"本表是`{snapshot['captured_at_utc']}`读取的{len(snapshot['issues'])}个Issue和{len(snapshot['pulls'])}个PR快照。",
        "其中包含本次117及成员116正在整理的文档任务，二者不冒称原实验。历史完成项、部分交付、失败和未完成均保留。",
        "",
        "执行阶段来自固定报告/任务原文；GitHub标签与PR合并是协作状态。in_review可以包含已执行实验，但没有要求的审查/合并时不写成done。任务可能在快照之后更新，恢复前须在线读回。",
        "",
        "| Issue | 负责人（实际assignee） | 执行成果范围 | 快照工作流 | PR快照 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for x in snapshot["issues"]:
        n = x["number"]
        labels = [l for l in x["labels"] if l.startswith("status:")]
        status = ",".join(labels) if labels else "未配置status标签"
        owners = ", ".join(x["assignees"]) or "未指定"
        plist = []
        for p in by_issue.get(n, []):
            state = "已合并" if p["merged_at"] else "草稿/未合并" if p["draft"] else p["state"] + "/未合并"
            plist.append(f"[PR{p['number']}]({p['url']}) {state}")
        lines.append(f"| [{n}]({x['url']}) {x['title']} | {owners} | {SUMMARIES[n][0]} | {x['state']} / {status} | {'；'.join(plist) or '本快照无关联PR'} |")
    lines.extend(["", "## 逐项说明", "", "每项保留原负责人和来源，不因为本教程汇总就接管其后续工作。", ""])
    for x in snapshot["issues"]:
        n = x["number"]
        kind, done, limits = SUMMARIES[n]
        sources = [s for s in manifest["sources"] if s.get("issue") == n and s["kind"] == "git-document"]
        links = [f"[{s['id'].upper()}](10-evidence-index.md#{s['id']})" for s in sources]
        if not links:
            links = [f"[T{n}原任务快照](10-evidence-index.md#t{n})"]
        lines.extend([
            f"### Issue{n} · {x['title']}", "",
            f"**实际成果：** {done}", "",
            f"**限制与接续：** {limits}", "",
            f"**证据入口：** {'、'.join(links)}；[当前Issue]({x['url']})。", "",
        ])
    lines.extend([
        "## 交付状态如何继续维护", "",
        "本次教程不更改上表原实验状态，不关闭别人的Issue，不合并原PR，不启动或取消服务器作业。Issue117的最终发布、检查和看板缺项记录在本任务交接。成员116的模型图册归档保持原范围。",
    ])
    write(DOC / "11-work-ledger.md", "\n".join(lines))


def full_edition() -> None:
    chapters = sorted(DOC.glob("[0-9][0-9]-*.md"))
    assert len(chapters) == 11
    text = [
        "# 从真实模型到Block电路：完整研究总报告", "",
        "2026-10-26；Liangruizhi；Issue117。本文由11章原文完整拼接，没有删节。",
        "章节分别阅读见[阅读入口](README.md)。章节内交叉链接保留到同目录独立文件，便于定位；本全文已包含其全部正文。",
        "这是一份已有证据的整理与教学分析；原实验、当前候选和制造验收严格分开，本次没有重新跑模型或电路。", "",
    ]
    for i, path in enumerate(chapters, 1):
        title = path.read_text(encoding="utf-8").splitlines()[0].lstrip("# ")
        text.append(f"{i}. [{title}](#full-ch{i:02})")
    text.append("")
    for i, path in enumerate(chapters, 1):
        text.extend(["---", "", f'<a id="full-ch{i:02}"></a>', "", path.read_text(encoding="utf-8").rstrip(), ""])
    write(DOC / "FULL_REPORT.md", "\n".join(text))


def main() -> None:
    manifest = json.loads((DOC / "source-index.json").read_text(encoding="utf-8"))
    snapshot = json.loads((WORK / "task-snapshot.json").read_text(encoding="utf-8"))
    evidence_directory(manifest)
    ledger(snapshot, manifest)
    full_edition()
    print("Built 10-evidence-index.md, 11-work-ledger.md and FULL_REPORT.md; no network or experiments.")


if __name__ == "__main__":
    main()
