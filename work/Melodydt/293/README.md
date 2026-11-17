# 七模型 200 MHz 评估

负责人 Melodydt；任务 https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/293 。

独立分支 `task/293-seven-model-200mhz`，基于 PR292 的 `5464d2794833f5e83afda875e0c264b7a43f3ea3`。本地根目录没有 Git 元数据，采用独立 `work/Melodydt/293/` 与 GitHub 对象 API 交付，避免修改同机主会话目录。

冻结基线为 `work/Melodydt/291/combined-results.json`，SHA-256 `741b593914265932c88c1b9924bdd80d8e8ae3e78e1652741cd66b4c3bf200e9`。不并入正在推进的 #280 新增算术标定。

核心周期 3334 ps 与 5000 ps 成对抽查，DDR 保持 630 ps；三路 P、512-bit SRAM、相同冻结计划和真实 512 位置 KV 历史。代表层使用原主控/局控页调度与 DRAMsim3 事务，恢复冻结输入残差后检查层输出及输出头 logits。抽样不是完整模型回放。

速度按各阶段成对比率及原全层时序重建；512-token Prefill 仍为未独立验证的条件估算。能耗复用原综合后无布线标定，区分动态、漏电、每事件增量和 DDR 驻留；按新时间重新积分。报告保留缺项和时序未签核限制，不声明完整芯片功耗。

远程独立目录：`~/LLMHardware/zenanyan/issue-293-200mhz-01`。仅向自己的任务目录写入；既有 runner 与资产只读绑定。所有作业 `--time=0` 并读回 `UNLIMITED`。

当前：脚本准备；尚无 200 MHz 测量结果。管理结构检查已通过，业务抽查待提交。登记 PR5 pending；看板能力缺失，待有权限人员同步，不能标记为已同步。
