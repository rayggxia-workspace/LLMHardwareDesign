# #127 支线交付与恢复入口

更新时间：2026-10-27 CST（Asia/Shanghai）；各批次时间与 commit 见 PR 回执。

- 仓库：[rayggxia-workspace/LLMHardwareDesign](https://github.com/rayggxia-workspace/LLMHardwareDesign)，project_id：`llm-hardware-design`；负责人：YUZE-LU。
- 任务：[Issue #127](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/127)；依赖：#121 / PR #122；交付：[PR #128](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/128)，未完成整个宏边界验收。
- 分支：`task/127-macro-boundary-qa`；固定起点 `8b62c2cf21f4d1b44e9a1f18e44713e0a73bec4d`。独立工作树：`D:/Data/电路实验/LLMHardwareDesign-worktrees/issue-127-macro-boundary-qa`。PR 暂以 `task/121-block-v1-twelve-layer` 为 base，便于只审查支线增量；正式 PR/交付 commit 记录在 Issue，避免文档自引用 commit。
- 正式代码与合同：`project/experiments/block_v1/macro_boundary_qa/`。本目录保存交接、合成控制、真实原生控制及候选诊断摘要；大体积原始产物留在授权存储。

## 已完成与实际验证

实现独立来源依赖检查、精确接口核验、可选时序/寄生数值合同比较、Linux 原生产物便携打包、实际 SPEF 图清单、原生 STA 双进程对照与证据复算、OBS 精确矩形并集覆盖及 ODB 导出入口。不导入主线 verifier，未改主线脚本/RTL/状态，不提交服务器任务、不占额外节点。二进制大文件使用流式哈希；本机 WSL 运行原生实验，真实大候选每进程一线程。

已执行：

```text
python -B -m unittest discover -s project/experiments/block_v1/macro_boundary_qa -v
python -B scripts/check_project.py
git diff --check
```

首轮为 36 项 synthetic 测试；原生诊断批增至 73 项，弧元数据/有符号差控制增至 80 项，修正版/流式几何/供电反篡改控制增至 93 项，分离 min/max 的声明/加载/私有补丁控制增至 100 项。另实际执行原生控制及 T6K 候选诊断。最终数量以测试回执为准。`synthetic-report.json` 的 passed 仅表示接收器逻辑控制通过，所有正式资格保持 false。生成用法：导入 `test_audit.Fixture` 在临时目录构造，再调用 `audit.audit(index_path)`；不使用任何真实候选文件。

历史 run164 的 PG 表示和 189 个保护单元来源问题已由主线 run168 修复，支线重新接收每路 30 个角色并验证通过。当前结果见《修正版接收报告_run168-169.md》与 `revised-candidate-summary-168-169.json`，旧报告保留历史失败。run168 原生测量上下文通过，仍分别有 958/900 项诊断超差，最大 slack 差为 107.274412/60.402183 ps。主线统一预算内运行 run169 只读 ODB 导出后，支线实际检查 A/C 的 9,208,361/9,206,675 个源金属矩形，未覆盖项均为 0。

另实际运行输出最短路径反例：0/8 级 BUF 支路控制的 max 输出差均低于 1 ps，但 8 级控制的 min 输出乐观差达到 230.138311/208.133455 ps。与固定 OpenSTA 源码的 max 路径选择一致，不能将当前 max 导出表直接视为已准确覆盖 min 输出。原始输入、输出、工具与代码摘要保存在 `native-output-path-control.json`。小 DFF 驱动/线阻控制和全部失败仍保留，未将复杂候选差异归为单一原因。

继续完成私有 min/max 分离原型和 24 组实际场景对照，并在同源 T6K A/C 上复验。输出 hold 最大差由 107.274/60.402 ps 降到 5.669/4.886 ps，max 聚合 slack 与原候选逐值相同；输入仍有 51.768/17.622 ps 乐观差。见《分离minmax原型报告.md》、`split-model-probe-summary.json` 及构建补丁；不是只留计划，也没有签发整模资格。原生工具和主线 exporter 保持原样。

输入 start-path arrival 归一化也已实际运行：四个 DFF 对照/两个 exact reread、T6K A/C 均未改善，后两路 1540 个聚合 slack 相对前轮变化为 0。已保留负结果、构建与测量 SHA，见《输入边界归一化负结果.md》及 `driver-boundary-negative-probe.json`；控制增至 102 项。源码核对确认输入 driver 的 load-dependent 部分附加在 wire arcs，报告显示位置与 Path 对象 arrival 不同；下一步区分驱动 Ceff 和真实输入 RC，不能减去整条 wire delay。

最新原生 driver 分量原型已继续完成：直接记录原生 `gate_delay-intrinsic_delay`，只从模型去嵌入此分量，真实输入 RC/slew 不变，分别构建私有 min/max。四个 DFF pair/两个 exact reread 和 T6K A/C 原生复验完成；低 R/同驱动通过原 1 ps 诊断。A/C 总超差降至192/110，slack 超差29/4，C无>1ps乐观聚合slack、仍有4项悲观及106项slew超差；A仍有9.834ps乐观差。完整资格仍false，控制增至105。见《原生驱动分量去嵌入报告.md》、`arc-driver-probe-summary.json` 与源补丁。

## 未完成与下一步

按用户继续监视/代跑要求，已在本机接续显式输出RC原生实验，无新增服务器allocation。已知DFF在两档R/三档load下完成12个whole/core model pair与2个exact reread；core+显式RC六个输出场景最大slack/slew差0.005330/0.004ps，whole高R高load时129.995570/178.927ps。已封存复核411个输出文件SHA，首个目录隔离拒绝失败也保留；控制115项。见《显式输出RC对照报告.md》及 `explicit-output-rc-summary.json` / `explicit-output-rc-index.json`。core输出参考面在RC前，不能直接替换现有M10物理pin模型；仍需主线审查真实集成/工作域，输入失败与正式资格false保持。

最新输入残差分解已绑定原 probe/pair/SDC 并真实复算：A/C各756项输入slack差由源/父层驱动分量差解释后，最大残差0.006171/0.006513ps；未校正原验收。slew分开核对后，A输入/输出17/146项、C输入/输出0/106项超差。另以原始工具实际完成输出1Ω/20kΩ八个model pair、四个exact reread，20kΩ输出slew差44.883ps、setup乐观差25.454305ps。控制增至112，详见《输入残差分解与输出线阻控制报告.md》及 `input-output-residual-summary.json`；不能只修输入而忽略输出模型工作域。

1. 原生 driver 归属已有改善证据；主线审查可维护的 min/max 与 driver 去嵌入合同。支线继续核对高R/不同驱动、Ceff/电容近似和port slew有效工作域，保留完整 V/SPEF/ODB flat 参考，不平行修改主线 exporter。
2. 来源、PG、完整 timing V 与实际 OBS 已取得本轮通过证据；OBS 不包含隐藏 transistor/GDS、DRC 或任意父层走线可达性资格。
3. 审查正式 flat/abstract 场景、全部适用弧/例外/corner/electrical 覆盖和容差。现有原生测量是 worst-per-boundary-edge 聚合，两个特殊 arc group 角色仍未完全分类，不能冒称全部弧等价。
4. 合格 C8 A/C 完整来源交付后逐一接收，继续补真实寄生归属与完整适用覆盖。不能把读回成功、无 active-net 判断的 annotation 清单或自报 ledger 当作完整证明。
5. 主线负责生产、物理/功能接收与正式冻结，支线交付可复算的通过或失败报告。#127 不关闭、不标 done；本批 PR 审查不代替整体完成。

恢复第一步：读取 #127 最新 Issue/PR 回执、《显式输出RC对照报告.md》、《输入残差分解与输出线阻控制报告.md》及《原生驱动分量去嵌入报告.md》，保留先前原型与负结果；核对 run160/161、run168/169 的来源/接口/OBS，再复算最新probe或接收主线新模型/C8。无需重新派生分支或接管主线活动作业。

## 协作接入回执

规则：rayggxia-project-collab 1.0.0。项目登记沿用 pending（management-hub PR #5 未确认合并）；没有 `config/board.json`，当前工具不具备 Projects 查询/写入能力，条目/字段 unverified、同步 pending，管理员待指定。优先级/截止时间未指定，不代填。审查人待指定，由主线安排集成；不自行合并。

共用 `progress/YUZE-LU/STATUS.md` 与主线 `docs/STATUS.md` 正由主线更新，本支线使用本任务独立记录及 Issue/PR 回执，避免覆写并行进度。
