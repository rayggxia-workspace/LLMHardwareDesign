# 执行与协作回执

规则：rayggxia-project-collab 1.0.0。项目`llm-hardware-design`，仓库rayggxia-workspace/LLMHardwareDesign，实际登录YUZE-LU。

- 任务：[Issue240](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/240)；成果沿用draft [PR241](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/241)，部分交付用Refs，不关闭Issue，不自合并。
- 隔离分支`task/240-ten-token-study`基于原PR241 `e7aeed2097f57a5f910cae70eb51a220c49a8a14`，通过普通fast-forward推送到该PR的已有远程分支`task/240-systemc-block-study`。发布前读回远程仍为e7aeed209，原研究本地工作树保持clean；没有覆盖#220或其他任务。
- 计时源提交`5a94faa1b`；最终M RTL提交`1bc6e0b04`；证据/报告提交`8accc6ecf`。本回执属后续文档提交，最终PR头以在线读回为准。
- 最终24项SystemC独立审计、61项边界/负向测试通过；GCC14.2/SystemC3.0.2严格编译通过；`verify_delivery.py`核对31份证据、12份源码，Git对象层43份SHA比对通过。
- 原生N作业101746 COMPLETED0:0、66440值/8419帧；原生M作业101753 COMPLETED0:0，K16/K32共242个最终响应逐位通过，各观察连续31拍II1。源、输入、工具、服务器路径和SHA见[manifest](manifest.json)。
- `scripts/check_project.py`和`git diff --cached --check`通过。原始回执以`-text`属性保留字节；仅为合法CRLF指定cr-at-eol，仍检查真实行尾空格、文件末空行、tab前空格。未改原件使其“通过”。
- 未完成：真实W8量化/KV完整数值、E32/scoreboard/存储/DMA/母控与局控联合RTL、新底座物理/端点/时序、能耗标定及同预算同质量FPGA对照。10.7298是102.4GB/s等新资源下的条件模型预测，目标尚未验收。
- 登记：沿用management-hub PR5 pending；缺`config/board.json`及Projects条目能力，看板unverified、同步pending，复用Issue7接入交接；管理员待指定。
- 任务当前in_progress，PR保持draft，审查人待指定。下一步从[结果及资源合同](RESULTS.md)进入联合RTL与数值合同，不能把预测速度或独立核功能证明当作系统完成。
