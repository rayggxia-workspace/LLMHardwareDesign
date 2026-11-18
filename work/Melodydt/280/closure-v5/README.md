# 三项能耗闭合工作 v5

负责人 Melodydt；Issue #280 / PR #281；任务分支 task/280-seven-model-energy，基线 2a2ada39a64d9bc473e89aa923d4077f72f90a64。独立子目录 closure-v5，避免覆盖 recurrent-step1 和 #293 的 200 MHz 成果。

本轮用户要求完成：七模型真实控制部署/路由/门控绑定和母控外围/精确驻留；读 DMA 综合后无寄生标定；特殊算子匹配 RTL、E32 周期差及资源重叠校准。M 时序闭合明确不作为前置条件。保持 #280 的 300 MHz、512-bit 数据 SRAM 和三 P，所有新 Slurm 作业 12 核、--time=0。

验收分开记录：

1. 模型实际加载的 RTL/参数/路由表/端口和门控证据有 SHA；逐窗状态驻留守恒；不能把静态服务计数标为 RTL 运行驻留。
2. 读 DMA 复用四份已完成综合映射，真实边界活动和对应空闲参考；核对标准单元链接、总线完整标注、窗口、事务数、单位及去重。phase 包含 shared，不能将两者总功耗叠加。仍明确边界活动传播与内部完整门级回放的区别。
3. 每个特殊算子有匹配的输入格式、指令与可综合 RTL；独立数值参考、实际样本和误差/溢出回执。E32 18 周期采用真实共享资源仲裁重跑，不能直接将旧总延迟翻倍；完整输出、DDR/SRAM 计数和资源重叠须重新核验。候选定点实现不自动替代冻结模型的已验收数值。
4. 七模型三窗双口径重新积分，PDF/JSON 更新并独立对账，原版本保留。部署或数值尚无证据的项目继续标未验收，不以成本代理冒充本轮 RTL 完成。

当前：BSCC 登录恢复；四版 DMA 综合结构检查 0 问题并链接成功，综合网表 SHA 见 dma_synth_power.py。共享版本的物理流程仍运行，phase 版本在 IO 引脚放置失败，不阻塞本轮综合后功耗。原四条物理功耗依赖不修改；本轮在独立目录运行无 SPEF 标定。

源码以本目录脚本交付 commit 和 inputs.sha256 记录。BSCC 工作目录 ~/LLMHardware/zenanyan/issue-280-bscc-t6-01/closure-v5-20261118；开源工具 ~/LLMHardware/opt。项目根目录无 .git，使用 Melodydt GitHub 连接、期望 HEAD 租约发布。原始大工件保留服务器，仓库保留脚本/小回执/散列。尚未完成本轮验收、PDF 或审查。

19:35 更新：当前有效链为 E32 `closure-v5-e32-9a2f2d23`、操作空闲与活动 `closure-v5-cal-278fbf5c`、实际单元引脚标注 `closure-v5-pins-30b6095c`。早期 idle 未完成 reset fence，边界/网名标定尚未标注内部引脚的结果仅保留诊断，不纳入新系数。特别不要采用旧 `dma-shared-state-calibration.json` 的正常空闲解释。

复现与验收入口：

```powershell
python scripts/check_project.py
python -B work/Melodydt/280/closure-v5/check_resource_intervals.py
python -B work/Melodydt/280/closure-v5/check_mapped_activity.py
python -B work/Melodydt/280/closure-v5/check_retained_pins.py
python -B work/Melodydt/280/closure-v5/deployment_report.py work/Melodydt/280/closure-v5/deployments work/Melodydt/280/closure-v5/deployment-audits
python -B work/Melodydt/280/closure-v5/integrate_calibrated_timing.py
python -B work/Melodydt/280/closure-v5/integrate_dma_scenarios.py
```

实验脚本使用 Python 3.10+；本机系统 Python 3.7 不适用于资源区间 AST 测试，实际已用捆绑 Python 3.12 运行。管理检查不代替业务验收。小回执、输入输出 SHA、具体服务器命令和仍缺少的完整物理绑定见[本轮交接](../../../../docs/handoffs/2026-11-18-issue-280-closure-v5.md)。新文件未进入 PR 前，仅算本地完成；最终上传版本以 PR 回执为准。
