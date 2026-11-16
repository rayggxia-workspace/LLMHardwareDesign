# 迭代5：同池条件尾部、阶段候选与原生多行复用

2026-11-09 CST，Issue219/PR220，负责人YUZE-LU；**部分交付，目标继续in_progress**。
后续更新：新计划数值101213已COMPLETED0:0、三输入逐位通过，见[迭代6终态回收](ALGORITHM_ROUND_6.md)。
以下保留本轮提交时状态，不把后续新tile证据混入本轮计划资格。
约20%算法收益、更多轮、完整KV decode、校准时间/能耗/token/s、充分适配ASIC/FPGA对照均未完成。

## 算法与共同后端分别记账

[阶段合同](../../../../project/experiments/block_synthesis/PHASE_COMPOUNDS.md)保留所有旧候选，
给合法的同前缀列分片增加父服务内FCFS描述符交接。孩子独占M/S/LC，父服务仍从共同起点到最后ACK
占有资源并集，不是一般跨任务事件前沿，也没有减少原标量搬运。
阶段符号程序的工作、原生命令、S和外存读写必须匹配原配方。
独立检查器重新构造程序与事件，再用旧连续预约检查器验证资源/依赖/缓存/连接。
共同阶段后端提供给贪心、旧DP、HEFT式基线及新排名；其收益不计为算法20%。

新增 `ConditionalTail`：每次前沿根据当前静态网并集排除未来无法合法使用的执行方式，
重算各任务乐观成本与DAG剩余最长链。网按全产品保留，不随层或时间释放。
相同候选成本特征合并，符号求值按完整时序/配方/命中键缓存；不包含模型名或固定实例数特例。
这是有限beam搜索排名，不能称全局最优。
另试 `net_resource_tail` 将已承诺的资源释放时间加入就绪任务估计；真实FFN上无收益且搜索代价更大，
只保留显式消融，不默认启用。

## 同池实际结果

真实首层FFN：88整数原语、74服务、2705候选（含84个阶段父服务），相同九组硬件/18束/每S16KiB。

| 同一个候选池 | 模型ticks |
| --- | ---: |
| 贪心 / HEFT式 / 条件贪心 | 11,261,130,658 |
| 原critical-bound DP | 14,177,752,236 |
| 条件尾部DP | **11,251,314,454** |
| 资源尾部贪心 / DP（独立Linux） | 11,261,130,658 |

新条件DP相对较强同池基线额外 **0.0871689%**，不是20%或整模型加速。
选中逻辑搬运593,161,155条，比贪心593,160,141略多；S峰值1023字，18束，独立成本/计划/阶段检查通过。
符号求值memo前后五个策略的实际任务、完成时间、搬运和网完全相同，memo只改善编译开销。
[完整FFN结果](results/column-phased-ffn-memo-review/summary.json)。

独立Linux复核资源尾部：贪心展开89327，DP展开710063，后者约62.8秒，仍没有超越11,251,314,454的已验证incumbent。
[负结果](results/column-round5-linux/ffn-resource-stdlib/summary.json)保留，不把它包装成改进。
策略在同一进程共享符号求值memo，不能用依次执行的wall-clock比较冷启动编译性能。

完整Qwen2.5-3B B1/S2、36层、无KV：Linux完整搜索已正常终态，原生工作量及全部计划独立检查通过。
贪心493,589,637,872、旧DP646,447,547,450、HEFT式493,688,216,816、条件贪心493,589,637,872，
条件DP **493,235,996,480**，相对较强同池基线额外 **0.0716468%**。
逻辑搬运26,318,566,205条，比贪心26,318,529,701略多；峰值S1023字、18束，253个阶段父服务。
条件DP搜索约1361.3秒，贪心约211.8秒，仍有编译开销；上述共享memo顺序不作冷启动性能排名。
[完整结果/独立审计](results/column-phased-full-linux/summary.json)及[原件存储SHA](results/column-phased-full-linux/storage.json)。
完整输入IR和全部计划已封存到任务服务器，压缩包SHA已双端核对；新选中计划的完整数值回放101213已提交，尚未通过。
早先[过程快照](results/column-round5-linux/full-live-process.txt)和[日志快照](results/column-round5-linux/full-live.log)保留为历史，不能代表终态。
Windows已完成贪心计划的当前动作族乐观下界406,736,524,963，最多还约17.60%重排空间；
只是当前动作族，不是硬件上限。阶段后端相对上一轮完成时间下降不计新算法收益。

## 不再只调排名：真实多行供数证据

针对A重复读65.8%、权重23.4%的审计，新增[原生多行探针](../../../../project/experiments/block_synthesis/ROW_TILE.md)。
使用main c4d7b960599b9d292f27eb4429d5f226a7156c95不变的M/P/S/feeder RTL和固定SHA的真实SRAM银行模型。
R=1/2/4/8，K=1/3/7/17，另R2/K2048；每K三个A分量、共享B、完整S64累加及最后一次舍入。
每行输出仍为原低S32标量槽，不假设动态打包或多列scatter。

84个四态RTL场景通过，覆盖正负边界/随机、half-even ties、shift0/8/16/24、完成背压和真实写ACK。
K2048/R2的B staging记录4096→2048，A仍12288；测试台周期753908→506100，
**包含host串行操作及故意背压，不是整机时间或300MHz时序签核**，不计DP20%。
故意将首例S64金值翻转1bit会触发RTL比较失败，负对照原件保留。
[全部结果](results/column-rowtile-v4/summary.json)、[握手日志](results/column-rowtile-v4/simulate.log)、
[源及输入SHA](results/column-rowtile-v4/manifest.json)。
尚未注册完整图候选：新staging与旧S[9:]前缀布局重叠，不能直接叠加命中收益。
先明确布局、可执行搬移、独立成本及数值回放，再给所有基线共用；不会把探针当整网验证。

## 检查、运行环境和失败

- Windows和独立Linux各157项通过，项目结构检查通过；没有删掉依赖失败检查。
  Linux使用本任务私有CPython3.12.8、libffi3.4.6、固定离线依赖，不修改系统Python。
  [Linux测试](results/column-round5-linux/tests-ffi.log)、[Windows测试](results/column-round5-linux/windows-final-tests.log)。
  Python源/库及Icarus源码SHA、文件回收回执见[汇总](results/column-round5-local-receipt.json)。
- Linux初次157项中29项因缺_ctypes失败；补私有libffi后全过，首次日志保留。
  私有Python无SSL，仅用于离线计算，不冒称通用联网环境。
- Windows完整搜索及资源尾部搜索出现未定位运行时异常：TypeError、堆损坏/访问异常；
  [原日志](results/column-round5-linux/windows-failures/)保留。尚无原因证明，不归因于芯片或断言Python缺陷。
  已改用独立Linux复核，不吞异常、返回不完整结果或重启仍在运行的完整搜索。
- 首次允许异构前缀的阶段候选触及精确事件上限，拒绝不完整时间；
  [失败程序/状态](results/column-phased-ffn-failure/greedy-failed-phase.json)保留。
  首版阶段动作族限制共同前缀配方，全部旧串行候选保留；这不是硬件不支持异构前缀的结论。
- Icarus10.1因SV语法支持编译失败；私有官方Icarus12源码构建后通过，不改目标RTL规避错误。
- 旧远程100911/100913/100925终态为依赖缺ortools失败，三个attempt原件各自SHA回收，
  见[失败目录](results/column-round5-remote-failures/)。修正PYTHONPATH后100970/100971均COMPLETED0:0、c64/c96、4CPU、UNLIMITED，
  冻结155项均通过。额外SystemC3.0.2两模式各6237阶段逐条匹配独立事件参考：23040/12660符号tick；
  [原件与6份SHA回收](results/column-round5-systemc/receipt.json)、[验证](results/column-round5-systemc/verification.json)。
  仍仅时序微实验，非RTL/整机时间/能量/token/s。
  100971重复确认旧资格化计划的完整搬运守恒，[5份SHA原件](results/column-round5-traffic/receipt.json)。
  早期冻结源的远程完整搜索100972仍RUNNING、UNLIMITED，不取消或重复提交；新选中计划数值101213另行验收。

## 下一轮验收入口

1. 保持远程完整搜索100972与新数值101213运行，终态后独立核对，不能以成本/调度审计替代新计划数值回放。
2. 将已证明多行路径登记成完整供数/命令/写回阶段；旧前缀候选保留，新布局/驻留不能免费复用。
3. 扩展真实可执行的中间值驻留与资源事件前沿；逐轮统计减少访问、重叠、共同后端及同池算法收益。
4. 继续#234/#235独立校准，加入KV decode和能量/性能对照；#236/#237记录硬件规模必要差距，
   已有Issue238跟踪原生M issue/drain瓶颈，不另造重复硬件结论。不能通过增加硬件凑固定基线算法20%。

规则rayggxia-project-collab1.0.0，项目llm-hardware-design；独立审查人待指定，不自合并/关闭。
登记management-hub PR5 pending；缺board配置/Projects能力，看板unverified/同步pending，沿用Issue7交接。
