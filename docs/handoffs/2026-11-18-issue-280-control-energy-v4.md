# 七模型控制补项 v4 与旧服务器接续

更新：2026-11-18 16:32 Asia/Shanghai。负责人 Melodydt。

- 仓库：rayggxia-workspace/LLMHardwareDesign；项目 llm-hardware-design。
- [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280)；[草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281)。
- 分支 `task/280-seven-model-energy`，PR 基分支 `task/274-seven-model-short-throughput`。
- 本地 `D:/Study_material/Study_material/LLMHardwareDesign` 是无 `.git` 的工作副本；通过 Melodydt GitHub 连接、保留期望 HEAD 的 ref 更新交付，不覆盖无关内容。
- 本轮远程作业脚本最后提交 `392913a8d98a33a6d6a2a2716c372d762c4d260e`；完整积分器、标定原始清单及七模型结果提交 `5ccf60c72c2790cfc08562380f123968fec3e2d1`，22 文件 Git blob SHA 已逐一读回核验。最终报告/状态文档随本交接所在提交交付，实际上传 SHA 以 PR 回执为准。没有直接合并主干。

## 完成范围与结果

已将三个非 DMA 方向推进到可复算的条件估算：母控核心启动/运行样本与 PM 取指，局控外壳/分发，交换机活跃流量。固定 512-bit 数据 SRAM、300 MHz、三 P、既有冻结时间/数值/DDR。完整 21 窗和每模型专项优化见 [25 页 PDF](../experiments/seven-model-energy-evaluation.pdf)。

第 2 步 Decode，单位 mJ/token：

| 模型 | 片上 | 片上 + DDR | 相对 v3 控制净增量 |
| --- | ---: | ---: | ---: |
| Qwen3-0.6B | 163.881–172.385 | 496.735–505.240 | 1.706–1.898 |
| Llama-3.2-1B | 203.893–214.753 | 657.379–668.239 | 2.150–2.391 |
| Granite | 169.186–182.381 | 523.164–536.358 | 1.758–1.955 |
| Phi-4-mini | 570.171–600.580 | 1872.557–1902.966 | 6.016–6.692 |
| Gemma-3-4B | 543.031–652.296 | 1754.626–1863.891 | 5.551–6.174 |
| Qwen3.5-4B | 707.795–1346.659 | 1951.730–2590.594 | 5.561–6.185 |
| Falcon-H1-3B | 732.241–1890.046 | 1630.485–2788.290 | 4.040–4.494 |

数值范围是样本与场景端点，不是置信区间或保证误差界。读 DMA 动态代理独立列示，不混入默认小计；沿用的写侧 DMA 已包含。

## 关键纠正与证据边界

1. 母控核心源码与旧 BSCC 标定三文件 SHA 相同，但真实实例 `SERVICE_STALL_LIMIT=2000000`，之前脚本误用了 4096。新综合网表按 FST 参数生成，STALL_LIMIT 仍为 4096；六运行窗重标。原 v3 文件保留，新 v4 替换旧核心项，不能简单再叠加一份母控功耗。
2. 启动采样从原始 100 MHz 时间 10000 到 500010000 ps，活动等比例重定时到 300 MHz。两工况各 15 次安装写、15 次读回，另有 35/27 次运行取指；核心启动参考约 15.8752–15.8761 mW。整个时间窗采用启动/运行样本范围一次积分，未声称已经测得模型精确状态驻留。
3. 局控私有副本切开 PM 和 scope_fetch 两个子模块，共 68 个非时钟/复位端点。四外壳、四实际路由器分别综合，48 窗全部边界标注；外壳每窗 5924 位、调度器 2894 位。四站点合计样本 12.193804–13.666608 mW。没有加入 PM 数组和描述符取指子模块的重复能耗；模型特有路由表仍未逐一硬件标定。
4. 交换机保留旧单元网络但不加载 SPEF 或估计线网 RC。六窗通过。采样器含触发起点计 20 个握手事件，VCD 可直接核验的内部事件为 TX 11 + RX 8，无重叠；首触发边沿缺少采样前状态。系数使用 19–20 次事件的敏感性，为 0.177930–0.288236 pJ/flit。只新增活跃差值，静默已有项保留。
5. PM 宏运行读沿用四宏的条件时钟弧增量，约 4.797071 pJ/读；不重复相加 OpenSTA 内部功耗。每条 compact 指令从 128-bit 控制 PM 读取一次；这与 512-bit **数据 SRAM** 是不同接口。
6. 21 窗静态遍历控制页并核验 SHA/CRC、CALL 分站点计数和页数量。每成功服务四 flit CALL + 四 flit 返回；取消/重试未计。静态计数不冒充 RTL 数值或时序回放。第 2 步 Decode 取指次数依次为 28859/26215/20167/49777/56211/63325/51341。
7. 六模型直接绑定当前冻结计划 SHA。Qwen3 采用已验收原始能耗 pilot：完整结果除重定位相关 `plan_sha256` 外与当前探针结果一致，再固定原计划 SHA 和各控制页 SHA/CRC。当前探针计划原件不在旧服务器，不宣称两个计划文件逐字节相同。
8. C639 原始源码 commit 待核实；不伪填为本轮脚本 commit。冻结源、复用静态库、网表、波形、工具库和输入页的 SHA 均在机器结果/服务器 `reused-model.sha256` 中，原始算术/TLM 版本沿用 v3 输入索引。

## 服务器、作业与可恢复命令

BSCC 两个网关地址已接受密码，但拒绝 `loginCluster` 会话。用户授权切回旧服务器后，显式使用已授权 `id_ed25519_server_ops_20261030` SSH 身份成功；未读取/提交私钥或密码。BSCC 上旧 DMA 作业本轮无法核验，不能引用旧快照当当前状态。

旧服务器 `yuzelu@10.129.166.172`；所有新写入在个人目录：

`/public/home/yuzelu/Melodydt/runs/issue-280/control-expansion-20261118-01`

四个最终作业均 node7、分区 c64、12 核、UNLIMITED、COMPLETED 0:0：

| 作业 / 名称 | 脚本 commit | 时长 | 结果目录 |
| --- | --- | --- | --- |
| 120297 / mdt-280swnew | 189b59945c8cb6278fd21816887df31a1d1e829f | 00:00:04 | switch-120297 |
| 120300 / mdt-280lcnew | 165083b11290a58af0a6ea59cf852b94f190a4bf | 00:01:34 | local-120300 |
| 120304 / mdt-280mcboot | 24bc1a567de5765da5fa326596060c90d54be808 | 00:02:24 | mother-120304 |
| 120313 / mdt-280ctlaudit | 392913a8d98a33a6d6a2a2716c372d762c4d260e | 00:00:04 | followup-120313 |

120313 复用 120310 已成功生成的六窗母控功耗，校验网表 SHA/真实参数；归档作业四秒不是重新综合的时长。采样/功耗使用 ORFS frozen SIF、Yosys 0.68+post、Verilator 5.042 复用模型和 Nangate45 typical Liberty，库 SHA `8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1`；OpenROAD 精确版本待核实，不编造版本号。

失败尝试保留：120298 是 VCD 总线范围遗漏，被完整性检查拦下，结果未采用；120301 因尚未创建的 FFN 激活日志中止后处理，后续以首激活时间晚于采样窗验证；120306/120309/120310 的母控六窗阶段已通过，计数阶段因计划定位、候选歧义、词表页键适配停止。最终静态复验和 120313 全部通过。

```bash
cd /public/home/yuzelu/Melodydt/runs/issue-280/control-expansion-20261118-01
# 以下四条为实际启动入口；复跑前恢复对应 commit 并重建脚本 SHA 清单。
sbatch --time=0 --job-name=mdt-280swnew run_control_gap.sbatch switch
sbatch --time=0 --job-name=mdt-280lcnew run_control_gap.sbatch local
sbatch --time=0 --job-name=mdt-280mcboot run_control_mother.sbatch
sbatch --time=0 --job-name=mdt-280ctlaudit run_control_followup.sbatch
# 仅查看已有任务，不会新提交：
squeue -j 120297,120300,120304,120313
sacct -j 120297,120300,120304,120313 --format=JobID,State,ExitCode,Elapsed,NodeList,Timelimit
tail -n 30 slurm-120313.log
cat followup-120313/mother-runtime.json
cat followup-120313/model-control-counts.json
sha256sum -c control-results.sha256
```

16:29 +08 快照，本轮个人 `mdt-280` 队列无活动作业；未查看/取消其他成员任务，未配置聊天结束后的自动监测。

## 本地成果、检查和复算

`work/Melodydt/280/control-gap-results/` 保存标定、全控制页清单、最终作业及服务器 SHA；`*_tlm_power_v4_control.json` 保存三窗明细、净增量、完整输入 SHA 和范围假设。25 页正式 PDF SHA：`ade48d5fe27ee3589a7d3f6b4049a1a1eb8cca0c77014ab0d144d18f806775fc`。v3 索引保留于 `energy_report_models_v3_arithmetic.json`。

实际通过：

```powershell
python scripts/check_project.py
python work/Melodydt/280/seven_model_control_estimate.py
python work/Melodydt/280/verify_control_estimate.py
# 下列使用具备 ReportLab / pypdf 的 Codex bundled Python：
python work/Melodydt/280/build_energy_report.py --output output/pdf/seven-model-energy-evaluation.pdf
python work/Melodydt/280/verify_energy_report_pdf.py output/pdf/seven-model-energy-evaluation.pdf
pdftoppm -r 75 -png output/pdf/seven-model-energy-evaluation.pdf tmp/pdfs/control-v4/page
```

管理检查不替代业务验证。21 窗分项/单位/原速度/原 DDR/原算术/去重/输入 SHA 通过；25 页 651 组数值核对通过，全页渲染及版式目检通过。新增整模型 RTL、完整内部门级回放、物理签核未执行。

## 所有剩余步骤

本轮三个方向已经给出条件估算，无运行等待。以下为提高硬件覆盖与准确性的后续范围，并非必须等待布局布线才能出本版：

1. 对各模型静态 provider 路由表/底座实例和门控做真实部署绑定，补对应控制样本；将当前 C639 迁移替换为模型匹配标定。
2. 补母控核心外的安装/序列/仲裁包装、packet bridge 和未采样启动状态；测量精确驻留，替换全窗样本范围。
3. 恢复 BSCC `loginCluster` 授权后核验旧 DMA 网表/作业；拿匹配综合输出直接做无 SPEF 的读 DMA 静默/动态标定，替换独立代理。不必等待布局布线。平台授权由用户/管理员处理，其余由 Melodydt 接续。
4. 特殊算子匹配定点/浮点 RTL、实际输入/溢出/误差验证及功耗；校准 E32 9/18 周期和资源重叠，再按需要重测时间。现有代理估算仍可使用。
5. M 300 MHz 时序闭合；若扩展完整芯片口径，再补全局时钟、跨块互连、PHY/封装/板级。布线后口径应单独版本，不混入当前无寄生报告。
6. 完成独立审查、PR 合并及协作登记/看板待办。没有审查/合并前不标 done。

恢复第一步：读取本交接与 PR 最新 HEAD，执行 `verify_control_estimate.py`；如继续补控制，先做第 1–2 项的模型路由/层级边界清单。不要重复启动已经通过的四个最终作业。

规则版本 rayggxia-project-collab 1.0.0。文件通过当前任务分支/草稿 PR 交付；Issue in_progress，独立审查人待指定，未合并。登记 management-hub PR #5 已读回 open/unmerged，pending。config/board.json 404，状态映射可读但缺 Projects 能力，条目 unverified、同步 pending，处理人有权限的项目维护者。各状态与本地完成分别记录。
