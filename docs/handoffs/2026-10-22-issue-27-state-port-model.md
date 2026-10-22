# Issue27：端口/状态实验交接

- 仓库：https://github.com/rayggxia-workspace/LLMHardwareDesign
- 任务：[Issue27](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/27)；[PR28](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/28)；负责人Liangruizhi，2663955430@qq.com，ID182389313。
- 分支task/27-state-port-model；独立工作树D:/Projects/LLMHardwareDesign-stateport；base task/23-qwen3-trace@7e0e82b7175525b3e113c791b7f1fc499b249443，依赖PR24→22→20→18→14→12。
- 正式运行source6ffb9417f0f01f614b733ce6c3ca9837906b3203，treeca3bc11b332a077aba8277284fdc5b9050ea9c66。结果提交和最新head从PR28读回；不能用结果commit替换实验source。该轮正式运行前后源树均清洁；交付后的未提交文件状态以恢复时git status为准。

## 已有证据

project/experiments/state_ports下资源DAG/四策略/小精确oracle、真实head捕获；docs/experiments/issue-27-state-port-model.md为完整报告。3456条件（1224可行/2232失败）、4896策略调度；真实Qwen3单头两shape的6在线核正例与10适用错误负例通过，2单tile控制明确N/A。两次资源run和两次真实采集的8科学payload逐字节一致。

25代码测试、6独立oracle测试、管理结构与限定路径空白检查通过。图/捕获/结果独立审计分别记录27073断言、399检查、3456例/108静态组/24完整witness；不把metadata审计说成独立重跑每一条未归档调度。图表PNG已视觉核验，SVG可导出；图表值不是芯片收益。

归档project/experiments/state_ports/results/issue-27-run01/evidence.zip，491436B，SHA256 f760dec66344c11fe9c7f04f55d91f610157d7ad624f6d66faa6a9bbdb1f1588。13成员原字节保存；本地D:/Projects/Codex/state-port-study-20261022/run-01、run-02、capture-01、capture-02保留供核验。权重/环境沿用D:/Projects/Codex/qwen3-inference-20261022/environment/，未上传Git，不声称已在共享存储。

## 研究含义与限制

同流量的O/m/l placement在1RW条件下最佳已找到cycle差异约4%，在本轮2RW best-of-four中消失。调度公平后一个decode表观差距从14.39%缩到3.37%；静态五链路可行性随逐bank容量改变。仅重命名Block零效应。尚无prefill/decode放置偏好反转证据。

全部服务参数是假设；FP32 attention核心不含投影、FFN、KV append、全部头/层与权重争用。单buffer事务只代表受限抽象调度，未验证RTL、实际scratch端口、FIFO深度、功耗和PPA。不将PR26的W8A8矩阵建议外推为INT8 KV/非线性。

最新协作：PR26固定2cd9ca15由huangpingyang04-lgtm推进benchmark；PR17固定0f58e74739c77cbfbca7e356af121a97529a48ca已有合并父层13通过物理/完整分层STA，但拆分配对与父层功能/RC覆盖仍缺；其ACT输出外部cap预算可用于下一阶段接口判据，不能当新attention微架构已校准。勿接管/覆盖这些成员范围或主动维护ref-project。

## 待完成与恢复第一步

1. 核验本人认证身份、origin、最新Issue/PR/评论、个人状态及相关未合并分支。读PR28实际head/CI与git status；本阶段待审查，不自行合并或标done。
2. 继续共同研究Goal（active，尚未达到最终Block/端到端证明）。优先选择可执行的精度与端口微架构合同，检验新attention/FFN数据路径与更强合法调度基线；同时扩差异结构并引入全模型权重/KV/端口队列，不再仅堆叠逻辑字节表。
3. 用合格物理输入约束内部资源与边界驱动/负载/布线/时序。若缺新宏或冻结合同，明确是假设，继续可独立完成的研究，不改他人进行中的物理实验。
4. 登记pending：management-hub PR5待合并；本仓库无config/board.json，当前会话无Projects工具，在线状态unverified/同步pending。具备能力管理员待指定，需要核验Issue27卡/Project ID/In review/Priority后读回；不自动新建看板或假定缺权限。

用户允许常规决策/实验/上传自主推进并记录理由。只在重要成果或原则性、无法独立解除的关键阻塞时提出问题；阶段交付不能虚标整个Goal完成。
