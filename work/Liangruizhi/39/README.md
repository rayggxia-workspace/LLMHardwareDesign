# Issue39本机实验记录

负责人Liangruizhi，2663955430@qq.com，ID182389313。独立工作目录D:/Projects/LLMHardwareDesign-kvscale，
分支task/39-kv-scale-boundary，base PR38@ec8fa3da13af29c22511977fcecb08f8cfd9a904。
任务https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/39。

开始核对main0cc36f3及README/AGENTS/project/协作/STATUS；PR38/34和Issue37/33仍待审查；
Issue32仍in_progress，PR36@62e97da9，继续Qwen修复，仅核任务范围和评论，不整合其结果。
指定GitHub账号查询通过；没有重复任务。共享状态/进度仅更新本人，其他worktree和ref-project不修改。

正式代码project/experiments/kv_scale，GPU可转交文案docs/handoffs/2026-10-23-gpu-codex-experiment-prompt.md。
任务临时/运行记录D:/Projects/Codex/kvscale-20261023；development01/02是dirty源码的探索，
首版12例direct，第二版24例加离线QK平衡；没有模型质量验收，无新增权重或远程任务。
首版发现K outlier导致直接量化约42.6%局部误差，按预定质量分层定位，并新增离线等价变换作诊断，
未按评价分数改变正式模型质量阈值。所有开发结果保留，正式结果以提交源码的run01/02及索引为准。

数学边界：RQ33合成测试（非真实Qwen2 bias）、独立Fraction；异scale PV先对齐再舍入；
真实V exponents若相同，相关错误实现负例记不适用，另有显式合成反例。
在线scale、因果流式定标、硬件转换/移位/宽加/除法和物理时序仍未闭合。

登记沿用management-hub PR5 pending；本仓库无board.json，连接器无Projects条目能力，
在线看板unverified/同步pending，管理员和审查人待指定。PR上传不代表审查、合并或done。
