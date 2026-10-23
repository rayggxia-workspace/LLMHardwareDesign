# Issue29继续执行入口

- 仓库rayggxia-workspace/LLMHardwareDesign；[Issue29](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/29)／[PR30](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/30)。唯一实际身份Liangruizhi／2663955430@qq.com／182389313。
- 分支task/29-port-rtl；独立工作树D:/Projects/LLMHardwareDesign-portrtl；base PR28@a3f8335287f6745bd96b9657a6279f12a142ac49。正式实验源码916dcf9e74ecd6a2164bdbb79991b0f3f7ed1b1e。结果提交与当前未提交改动恢复时查PR30及git status；不把结果commit替代实验source。
- 用户本轮问解决情况，已说明“判据与局部证据已建立，最终跨模型Block方案/端到端收益仍未解决”。此问题未取消持续Goal或要求停止研究；常规工作继续自主推进。

## 已验证

Slurm89836／89837（8CPU）COMPLETED0，正式27config、1872program、54stress各运行两次，27份results.json逐字节一致。管理结构、9项checker测试、本机ModelSim9组smoke通过。独立全量结果1698897项；33个保存witness逐拍2482636项、2191来源绑定、8真实变异通过。最初审计误把decode未请求padding强制初始化产生12个false FAIL，audit01原样保留，audit02按既定语义mask纠正；未放宽已请求数据要求。

完整报告docs/experiments/issue-29-port-rtl.md；证据ZIP与索引在project/experiments/port_rtl/results/issue-29-run01；独立工具及报告work/Liangruizhi/29。大证据已存/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-29/并核SHA；本机D:/Projects/Codex/port-rtl-study-20261022/保留正式包、开发失败、旧审计和二次结果。详见报告各SHA，未依赖C盘新建缓存。

1RW同库存下p000→111 best-of-four改善prefill1.46%／decode1.71%；2RW八placement等效。720匹配禁边案例完整结果不变，54静态选择组均有共同placement达到两个phase各自最佳已找到值。本轮没有phase放置冲突证据，也没有证明芯片/PPA或跨模型方法优胜。M/V仍合成计算延迟、未实现完整scratch/DMA。

## 正在进行与恢复第一步

1. 核验认证身份、origin、最新Issue/PR/个人状态和其他成员进度。继续遵守协作Skill，不自合并或标done。
2. **首先阅读已归档的89838超时日志与诊断，再执行单配置分阶段综合检查**。在/public/home/yuzelu/RuizhiLiang/issue29-port-rtl-20261022/formal01/运行通用Yosys检查；脚本为synth-job.sh／synth-check.sh，对应副本在work/Liangruizhi/29。最后观察仍在首个mode0/depth1的前端展开阶段，尚无通用综合通过证据。读取synth-89838.log和synth-check目录，保留失败或超时，不把仿真PASS当综合PASS；不能声称已完成SRAM宏映射、实际面积、布线或STA。只管理本人job。
3. 当前PR draft、Issue in_progress，待完成通用综合检查及相应报告更新后再决定本阶段交付状态。固定源码/仿真证据已保存且已上传，继续结果交付不重跑无变化业务。
4. 下一项高价值研究需要完整权重/KV/投影/FFN、多头层与差异架构，和真实算术/宏端口/驱动/布线预算；不要仅继续增加这个小图的配置数量。所有假设服务周期保留限制，任何改动与基线使用相同资源和相同策略搜索。
5. PR17最新核对ce5896d已经形成成对H1结果，独立复算area+0.412%、wire+7.142%、via+2.974%，不得复述旧未配对结论。另有3文本Git LF字节与原生成CRLF SHA差异，独立报告保留失败及诊断；没有替他修改源证明。待处理人待指定，不把该问题与数值错误混为一谈，也不能声称字节全PASS。H1不是H2，更不是本attention的物理校准。

登记沿用management-hub PR5 pending；本地无board.json且当前无Projects工具，在线状态unverified／同步pending。管理员待指定，需核验Issue29条目/Project ID/Status/Priority后读回。PR审查人待指定，未合并/未验收，整体研究目标未完成，当前平台状态见下条核验。

## 平台目标状态核验

2026-10-23重新调用get_goal核验：平台目标实际为blocked，工具未返回该状态的历史原因；此前沿用active的文字不代表当前平台状态。研究目标尚未完成，本轮依既有授权继续执行并完成实验交付；平台自动续跑尚未恢复，恢复由用户/系统控制，不能以Issue进度或本地文档代替。

## 综合前端诊断

独立只读诊断见work/Liangruizhi/29/audits/synth-diagnosis.md，快照保存原始log和源码SHA。默认RESP_DEPTH2的read_verilog已完成，当前为PORT_MODE0/RESP_DEPTH1重新derive；尚未进入proc/memory_collect完成点。未见bank_mem转寄存器警告，不能凭耗时断言SRAM已FF展开。若当前作业超时，下一步使用同源码单配置read_verilog -defer; hierarchy后保存RTLIL检查点，再分开执行proc/opt/memory_collect，记录时间和内存。该建议尚未执行；不先扩九配置，不把通用memory视作宏映射。

## 89838最终状态

通用Yosys作业89838于2026-10-23 09:55:54 CST达到20分钟时限，Slurm最终TIMEOUT（elapsed20:28，batch0:15）。日志确认已进入PROC_MUX，未完成后续memory_collect/check/stat/JSON；未证明综合通过，也不能把工具超时解释为RTL功能错误。原始日志和SHA索引已保存work/Liangruizhi/29/audits/synth-timeout01/。 下一步保留同一源码，使用单配置-defer与RTLIL检查点分开前端和proc成本；该后续检查尚未执行。先前运行中快照仅代表其采集时刻。
