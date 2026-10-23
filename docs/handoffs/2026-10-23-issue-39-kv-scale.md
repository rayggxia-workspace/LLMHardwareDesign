# Issue39交接

- 仓库https://github.com/rayggxia-workspace/LLMHardwareDesign；project_id llm-hardware-design。
- Issue39 / PR40，负责人Liangruizhi，2663955430@qq.com，182389313；指定连接认证核验。
- 独立D:/Projects/LLMHardwareDesign-kvscale，task/39-kv-scale-boundary；base PR38@ec8fa3d，依赖PR34。
  正式实验源码a83e624a10ecc3f012eff2f2f770c9f9842c3a76；交付commit以PR40 head为准。
  除本Issue文件无其他改动；交付后实际工作区/commit在PR回执，恢复先检查，不覆盖后续改动。
- [实验记录](../experiments/issue-39-kv-scale-boundary.md)，project/experiments/kv_scale代码/配置/结果index/归档；
  work/Liangruizhi/39包含独立输入审计、打包/安全提取、检查和交付manifest。
- 实际本机24组合两次运行，89280整数比较、296448来源值/540指数、11边界测试和管理检查通过；
  五科学文件逐字节复现。真实K错误scale六负例检出、42不适用；真实异V scale未捕获，仅合成反例。
  direct/离线balance误差与所有失败保留，不能称模型质量、在线scale或芯片收益通过。
- 未做：新权重、完整量化模型/多头全层、GPU/长模型推理、在线scale硬件、RQ33 RTL、宽向量物理或端到端性能。
  只用了既存Issue27真实输入，不整合师兄结果或操作其他成员worktree/ref-project。
- 临时/开发/正式独立输出D:/Projects/Codex/kvscale-20261023；开发01/02不是正式证据，留作方法演进记录。
  正式有效成果已归档，保留恢复需要的原始文件；没有删除其他任务临时目录。

恢复第一步：核GitHub身份、最新Issue39/PR40、Issue32范围与新评论、AGENTS/Skill及成员交接。
读本报告后运行verify.py核SHA/提取，audit.py核独立整数，audit_inputs.py核真实来源；
首次正式sourcecommit和实际运行命令在manifest/README。若继续整数研究，优先冻结因果scale/缓存版本和
跨GQA共享变换，分别实现前端定点转换/宽归约资源，再做同精度物理可行性，不能仅调低局部误差。

用户可转交[师兄Codex文案](2026-10-23-gpu-codex-experiment-prompt.md)。GPU执行仍由师兄原任务及后续认领，
本机方不启动；Gemma许可/配置未获授权时待处理，Phi策略未冻结时保留。用户通知兄方完成后，
才读取最新结果/PR/原始文件/SHA并整合。数据共享位置/缺少字段按真实条件记录，不称本地保存等于远端可读。

登记沿用management-hub PR5 pending；无board.json/Projects工具，在线看板unverified/同步pending，
管理员/审查人待指定。PR待审查合并，Issue只in_review，不done。
