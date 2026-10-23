# Issue33本机整数阶段交接

- 仓库：https://github.com/rayggxia-workspace/LLMHardwareDesign；project_id llm-hardware-design。
- 负责人Liangruizhi，2663955430@qq.com，ID182389313；本轮认证已复核，禁止切换其他凭据。
- [Issue33](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/33) / [PR34](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/34)，
  task/33-int8-contract，base task/29-port-rtl；独立D:/Projects/LLMHardwareDesign-integer。
- 最终源码03be205018356a36788cb3e5faf01d707cb74a1c；实际捕获db74f40e，scale/refinement分别60cc1b7/fb94abcc。
  结果/本交接的交付commit以PR34最新head为准，不能把源码commit当作包含全部结果的提交。
- 原始科学文件为evidence/issue-33-local.zip的30个成员；本地inputs/results/results-v2是被gitignore的展开副本，
  按manifest绑定，已随归档交付。运行verify_evidence.py --extract会拒绝覆盖不同字节的已有文件。
- 正式工具/inputs/results/results-v2在project/experiments/integer_precision；最终报告docs/experiments/issue-33-integer-precision.md；
  原始检查/RTL日志、来源审计、最终manifest在work/Liangruizhi/33。完整源码/配置/数据位置/SHA由各报告和manifest关联。
- 本轮只修改Issue33范围，未修改其他成员进度、ref-project或其他worktree。提交后的实际git状态由PR回执读回；
  恢复时重新git status --short确认，无权覆盖他人新改动。临时/仿真库只在D:/Projects/Codex/int8-contract-20261023。

## 实际验证和边界

管理结构、20业务测试、1028 RTL用例通过；26拍RQ延迟/28拍启动间隔。
实际Qwen3捕获34数组、3,105,456B NPZ，SHA daa1c2d1b32fee434dbb82340a803979eca14a33a06057d6abdd3f4a4a210402。
两实际格式包共20payload、256输出经独立整数/Fraction重放；48组W8A8输出精度、36组KV细化；
4608图点、2214可行，最终审计227源码绑定/19日志绑定、逐点容量和beat核对通过。
首次RTL语法失败与私有状态工作区漏计已保留/更正；初版placement.json不作为完整缓冲证据。

旧FP32/BF16结果不变。新工具是候选整数参考/合成服务，不是全整数模型、真实INT8速度或物理Block。
P7在长度256/512均匀行全零；短校准导致KV/部分线性输出裁剪，不能因位宽变大便判质量通过。
完整参考数值包缺失、在线整数scale、部分宽算术RTL、宏映射/PPA/时序和真实GPU质量仍未完成。

## 待同步和处理人

- PR待审查/合并，审查人待指定；不自合并、不done。Issue在线状态以回执/读回为准。
- 登记沿用management-hub PR5 pending；无board.json、无Projects工具，在线看板unverified、同步pending，管理员待指定。
- 师兄实验需求已写GPU_CAPTURE_CONTRACT.md；16GB显卡优先Qwen3.5-4B，Qwen3-4B不必跑。
  未收到兄方实际结果，不安排其任务或声称已采集；由用户通知后才检查整合。
- 没有启动服务器、新大模型下载、长上下文/多模型GPU作业。此前其他Issue的远端状态不由本交接更新。

恢复第一步：用户通知师兄完成后，核对Liangruizhi认证、最新README/AGENTS/Skill、Issue/PR/评论和
兄方未合并分支的交接，验证结果位置与SHA；用capture.py严格接收、--expected-commit/--expected-revision
核来源，适用线性包用--replay-linear；再依据真实质量筛精度，并以同精度/库存重建划分比较。
未通知时保持本机交接，不自动读作兄方完成，不重复大模型测量。
