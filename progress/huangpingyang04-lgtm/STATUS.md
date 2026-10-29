# huangpingyang04-lgtm 的进度

历史检查点：2026-10-27 11:13 CST；当前结果及唯一最新索引见文末 current-buffer-PG-status。

[Issue55](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/55)，[草稿PR58](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/58)。阶段一已交付；二/三未验收、四未执行；主要候选1/3，无冻结。

此前检查点（历史，非当前结论）：原wire-only共同钟线6/6入口slew失败。新75个无状态正向buffer的共同CTS/合法放置/独立读回通过，76逻辑clock网通达6入口，原6宏PIN/OBS与PG/reset严格保持；150个真实电源PIN及坐标变换已核对，但新缓冲器只有逻辑供电，真实PG和钟线布线/RC未完成。LL新ABC候选全布线/DRC0/全网/65545状态168074锥通过，但3ns实测setup−2.151527ns/hold−0.547693ns、slew98/cap2548失败，不替换当前主线。无冻结或最终定制。

- open原20例、三seed两次host任务、162 VPU/控制与120 MM/QACT有限回归及独立证据通过；LL180连续任务/540完整内存通过；不是全输入证明。
- 当前两辅助state-cone/M8/RC锚点/抽象PIN/OBS/model link资格通过；新辅助时序与VECTOR新增/恶化未解，不归继承。另一全规模LL候选布线92018继续，不重复/停止。
- 92044方向bug、92071 cut间距、92078旧图断开失败保留；92085新点集fixture/92087规划通过，没有放宽规则、移动Block或切换M11/M12。
- 新任务4核，线程匹配。92063用7:04/CPU8:31.805，均1.21核；92064用13:21/CPU13:30.398，均1.01核；92026用25:08/CPU25:11.394，均1.00核。未停止/在线切换旧作业，不称四倍提速。
- 恢复先读最新milestone与driver/submission/source_revision/spec，再核对sacct，避免重复。92026新源PG独立检查、92063全六资源held-reset、92064当前13局部接入已各自通过；核查92087完整5网原生读回和92018候选完整布线。继续active+idle任务/物理parking、时钟质量RC及新增时序问题，再冻结和两完整案例M9/M10定制。freeze/route仍未实现，无阶段二/三/四验收或新远端push。
- 远端仅阶段一，无新push；登记pending、看板unverified/同步pending、审查人待指定，不合并/关闭。

<!-- current-buffer-PG-status -->

更新时间 2026-10-29T17:38:16.760392+00:00；截止北京时间2026-10-30 09:19:06。候选1/3未冻结，M1–M8固定、M9/M10及via8_0/via9_0定制，M11/M12未启用。

当前同一完整六资源数字模型：93540 openTPU20组、93541 llaccel180任务均通过工作+对端保持复位有限门级回归（实际负例/33SRAM保护）；无SDF或最终物理底座证明。VECTOR第二实际布线原27DRC不变，但224时序端点恶化/cap31，未通过；93559确认原时钟几何不变而邻网_173771_耦合变化使接收时钟提前。AUX setup−1.571848ns/hold−0.248454ns/cap1047仍不达标，具体ATTN输出拼接与gemm_a_req[7]到SRAM bank选择路径已定位。93534完整父层原生CUGR运行，尚无最终布线；旧93130超时失败，不再记为运行。底座未冻结、两版最终定制布线/总验收未完成，外部时钟波形及37负载仍null。

详细状态/范围/对象/证据见 docs/experiments/issue-55-full-block-integration.md 和 project/experiments/block_full_integration/results/summary.json。索引 /public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/convergence-12h-20261029T131906Z/records/milestone-20261029T173816Z.json，SHA-256 1068f85b683ae9ccf03049ba3ecd2e37337f794e3cc09112621cb7c695ec7dec；工程487cb63c5d105e485529352c8d2cb8773927a254。大文件留服务器，沿用Issue55/PR58草稿；登记PR5 pending、Projects未核验、审查人待指定。


<!-- block-layout-routing-lessons-20261029 -->

经验积累（2026-10-29，UTC+8）：补充[Block 划分后的布局布线问题与处理经验](../../docs/experiments/issue-55-block-layout-routing-lessons.md)，Refs #55 / PR58。区分受保护原单元与新增缓冲器位置、具名填充替换和 PG 金属保持；记录 AP/via/短引线预筛、实际布线、完整 DRC、RC/时序与功能的不同门槛，以及 AUX45 仍未解决的反例。文档依据18:00的只读快照，后续实验状态以主任务最新回执为准；本次仅文档/轻量索引，不启动或改动主线实验，不改变底座冻结及任务验收状态。服务器独立交付包：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/deliverables/block-layout-routing-lessons-20261029T100718184702Z；证据索引 SHA-256：96da8e3ee0c638a3ba9fddfad8399fd61334d7431dcd3255afd4a64d79955b97。
