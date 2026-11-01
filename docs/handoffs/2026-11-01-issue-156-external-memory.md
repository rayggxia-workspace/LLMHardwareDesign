# Issue156 外存接口交接

仓库：https://github.com/rayggxia-workspace/LLMHardwareDesign ；项目 `llm-hardware-design`。
任务：https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/156 ；负责人 YUZE-LU。
分支：`task/156-external-memory`；冻结父提交 `33d87f6868d98befe0aa01bf9c5725fe7ef47a40`。
最终提交通过本分支 Git 历史和 PR head 核对，未自行合并。

成果入口：[合同](../EXTERNAL_MEMORY_V1.md)、[证据](../../work/YUZE-LU/156/README.md)。
标准单元 S 和 #155 SRAM 接口各三种真实初态的联合 RTL 验证通过；新 DMA 单独严格 lint、
Nangate45 综合映射通过。未修改七宏 RTL 或 #155 文件，未更改既有远程作业。

本分支以 #155 的既有远端提交为父，审查 PR 以 `task/155-s-sram` 为 base，避免将
尚未进入 main 的七宏源和 #155 物理工作混为本任务的改动。只在依赖主线合并后再按实际
状态调整目标；不可把 #155 后续变更重写或强推掉。

需审查：DMA 的所有权、错误后排空和 T 长度不匹配的协调恢复；外部顺序响应协议；
软件仍承担的命令桥／打包／调度；新 DMA 的最终物理归属。不能以本次 RTL／综合结果
替代 DMA 布局布线、#155 真实 SRAM、或七宏的物理／时序／形式验收。

恢复入口：先读最新 Issue/PR 和 `work/YUZE-LU/156/rtl-final/result.json`，核对当前源 SHA。
若 #155 改变 S 的协议、时钟或有效延迟，重跑双 S 联合验证；若仅产生物理视图，则另外
验证其与这里冻结接口的实际一致性，不复制本次接口仿真作为真实宏物理通过证据。

登记沿用 management-hub PR #5 的 pending 记录。当前仓库没有 `config/board.json`，
只有 `config/status-mapping.json`；本会话没有已核验的目标 Projects 条目，事实 unverified，
同步动作 pending。待指定管理员提供目标看板和权限后，核验 #156 assignee、条目及
Project ID/Status/Priority 字段并读回保存；不能另建看板或自称已同步。审查人待指定。
