# Issue181 / PR182：分组仲裁与多S DMA RTL交接

2026-11-04，Asia/Shanghai；负责人huangpingyang04-lgtm；规则rayggxia-project-collab1.0.0。

- 仓库https://github.com/rayggxia-workspace/LLMHardwareDesign；[Issue181](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/181)、[PR182](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/182)。沿用`task/181-multi-s-hbm`，不新建PR、不自合并。
- 输入commit `a216087e4e1b60b46f7ae35932baf8b4a6e4fdb6`，base main `4b1df2c7`。原S/feeder/M及异步FIFO未改。
- [RTL合同](../HBM_GROUP_DMA.md)、[最终服务器结果](../experiments/issue-181-hbm-rtl-results.md)、[原件实收及独立审计](../../work/huangpingyang04-lgtm/181/README.md)。
- 实际检查：38场景、6×38 RTL非法输入拒绝、坏payload预期失败、238矩阵15232结果、6912294运行检查；4S/16S DMA核心完整Yosys通用综合/check-assert，无锁存器；Verilator lint/C++Werror通过。独立核验及3个篡改负例通过，原始warning/失败保留。
- 最终Slurm97178，c64/node1、4CPU、UNLIMITED、COMPLETED0:0；服务器`/public/home/yuzelu/PingyangHuang/issue181-hbm-rtl03-20261104`。首次97176夹具编译失败保留；97177中轮成功。三项作业均自然结束，无本任务残留作业；未动其他任务。
- 新RTL实现组间/组内轮询、有限槽/信用、描述符/地址、LOAD到S写ACK、STORE到外存写响应、完成背压、错误排空及ID归属检查。C++不再选择搬运源或维护硬件信用。
- 审查重点：多并发状态更新、槽代次及复用、相同S响应顺序、错误后已分配工作排空、描述符上下边界、复位必须覆盖外存队列、通道配置在活动任务期间固定。
- 未完成：完整AXI/真实HBM控制器/PHY及器件时序校准、control_d/系统主控实际替换接入、M结果适配器、工艺映射/物理时序/扇出/面积/功耗/封装。通用综合不替代这些验收。
- 恢复入口：先核对Issue/PR最新状态，然后`python -X utf8 -B project/experiments/hbm_feed/check_rtl_evidence.py`。后续新增硬件范围需明确依赖与验收，不覆盖本证据。
- 登记management-hubPR5 pending，config/board.json缺失，当前无Projects条目/字段工具，看板unverified/同步pending；管理员及独立审查人待指定。Issue保持in_review，PR待审查、不标done。
