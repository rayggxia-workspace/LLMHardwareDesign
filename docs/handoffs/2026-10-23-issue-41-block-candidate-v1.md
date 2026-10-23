# Issue41：具体Block候选和最小实验交接

- 仓库https://github.com/rayggxia-workspace/LLMHardwareDesign，project_id llm-hardware-design。
- Issue41 / [PR44](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/44)，负责人Liangruizhi，
  2663955430@qq.com，ID182389313，指定认证核验；审查人待指定。
- task/41-block-candidate-v1，独立D:/Projects/LLMHardwareDesign-blockv1，base PR40@f2e55e0。
  解析/设计源码dfb12cddb81f6acdf44a2c1f64600aa37e121a3a，交付commit以PR44 head为准。
  交付只包含本任务文件；最终工作区状态和head由PR回执读回，恢复先检查新改动。
- 正式方案docs/BLOCK_CANDIDATE_V1.md，最小实验docs/BLOCK_MINIMAL_EXPERIMENTS_V1.md；
  机器合同/解析工具project/experiments/block_candidate；analysis/checks/manifest/verify在work/Liangruizhi/41。
- 设计覆盖M/V/A/R/S/D计算、状态、接口和预连线；D1–D6六分叉，E1门、E2/E3/E4三边界判别、E5冻结接受。
  464KiB/281乘法器只是声明区域，score spill/RQ瓶颈/全模型state不常驻为解析反例，不是芯片测量。
- 实际验证：管理检查、whitespace、两次解析逐字节重现、三源码版本绑定、8已知值、两个容量反例、
  D1–D6覆盖与新文档相对链接；交付SHA由verify.py复核。所有E1–E5新执行均未做，不能标实验通过。
- 没有新权重/模型/RTL/GPU/远程任务；没有整合师兄结果，没有修改其他worktree/他人进度/ref-project。
- 临时/准备/原始解析D:/Projects/Codex/block-candidate-20261023保留以复查；正式小JSON/日志入库，未删其他任务文件。

## 恢复第一步与分工

先核指定GitHub身份、最新AGENTS/Skill、Issue41/PR44及评论、Issue32/31/42/43最新范围、成员交接。
运行`python -B work/Liangruizhi/41/verify.py`核交付/源版本；读两份正式文档。
随后只挑E1仍缺的因果scale/GQA共享/格式边界验证，数值门闭合才跑E2/E3；
E4缺新宏/工艺/冻结资产时保留pending，不套用openTPU旧物理合格证；E5策略冻结后再做Phi。

并行核对：Issue32/PR36仍由YUZE-LU修Qwen，等用户完成通知才整合；Issue31/PR35物理不接管。
本轮交付期间新增Issue42两控制锥方法与Issue43五加速器资源约束，均huangpingyang04-lgtm，
范围与本候选互补；仅核任务范围，不代其成果验收或复制其资料。
Issue43后续官方资源约束可修订示例库存，但当前数字不是从B数推导的最终芯片数量。

登记沿用management-hub PR5 pending；无board.json/Projects条目工具，实际看板unverified/同步pending，
管理员待指定。PR待审查/合并，Issue in_review非done；不自合并，不把分析候选写成实验或硬件完成。
