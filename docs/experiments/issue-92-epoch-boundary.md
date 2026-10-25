# Issue92：32位epoch终止态排空及配置/完成优先级

2026-10-25，负责人Liangruizhi。[Issue92](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/92)，task/92-epoch-boundary，基于[Issue85/PR89](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/89) eef976d。本轮源码、实际验证和归档已完成；本子任务尚未push/开PR，交主会话统一上传和同步，待审查合并而非done。

## 实际缺陷与最小修复

原RTL会拒绝最大epoch的新命令，但最后合法命令从0xfffffffe递增到0xffffffff后若soft_abort，epoch不能再递增，memory_link被复位为idle。迟到的相同tag响应仍被判断为匹配，ext_take取idle link_take=0，因而无法排空。原RTL的完整边界仿真和真实门锥SAT均实际复现；原失败未删除。

在原chain85中加入组合terminal_discard=max&&(soft_abort||state==0)，并与tag不匹配条件合并。丢弃路径返回take且不向link发布valid，计入stale_responses。最后合法命令处于活动状态时，同tag正常返回仍保留。无新状态、队列或算术单元，32位计数不缩小、不回卷、不在max接受新命令。

复核发现cfg_ready/cfg_valid/done在reset或soft_abort同拍仍可能对外显示握手，而store/FSM复位优先使该事务被取消。现以!core_reset屏蔽usecfg、cfg_ready、cfg_valid和done。合同明确：发起reset/abort的控制器同步取消pending cfg并在恢复后重试；此前已经写入SRAM的数据保留，不承诺事务回滚。busy不是命令接收资格；只按cmd_ready/cmd_accept交付。

只有核心与外部fabric协调硬复位才能从耗尽态重新开始；独立核心reset后仍保留旧tag事务不在合同内。此规则是显式系统义务，不能靠wrap或复用tag掩盖。

## 同版真实RTL与数值证据

正式RTL、驱动、证明与接收源码均为71824cc8bbe0fe53b0b770abacd1b74e6f1b942c（phase4），其完整命令和Slurm资源在work/Liangruizhi/92/execution.json。全部实际整数参考、Verilator、Yosys SAT/映射和全量字节接收均仅本人CPU服务器lrz-i92-*执行。没有下载模型、启动其他机器或修改其他成员任务。

|实际检查|范围|结果|
|---|---|---|
|原85完整消费者/恢复回归|quiet/backpressure各30完整命令，共60；六个Granite既有输入、两cache模式|实际acc/down/merge/norm逐位等于独立NumPy/bigint参考|
|max最后命令与协调reset重启|两路各2完整交付输出，共4|完整整数数组逐位接收；无host中间结果注入|
|耗尽态拒收|两路各48个实际cmd保持周期|不接受、不回卷、不发新外部请求|
|终止响应排空|两路各5个same/different tag响应|实测stale计数递增且无幽灵完成|
|max处中止|两路各2个，包含同拍响应/abort|清空消费者并保持max|
|配置冲突|两路各4个：idle request/pending response × hard/soft reset|无假握手、无取消写入、恢复可配置|
|done+ack+abort|两路各1个真正算完但未交付命令|abort优先，不发布done，未计为完整交付输出|
|严格接收负例|实际改输出码；空/错类型/错误最终epoch/额外协议字段|拒绝；旧85接收还核完整协议及实际语义负例|

边界驱动仅在idle/空fabric对Verilator实际公开的32位epoch寄存器作一次性边界注入并读回、跨边检查保持，然后执行原RTL命令/流水/响应逻辑。每路4次注入有实测计数；这是声明的验证后门，没有向生产RTL添加写寄存器端口，也没有等待2^32次命令。早期phase1–3结果保留，但不能叠加为更多独立样本。

## 真实下一状态门锥证明

Yosys proc从实际chain85.sv生成原始网表；提取真实32位epoch $dff的D和实际命令/响应/配置/完成信号，递归保留原组合单元、参数和逐pin连接。当前epoch/state/pending的Q及link_take/rready/rvalid是声明的自由输入，覆盖全部当前位模式，不自行重写FSM来代替RTL。

修复版46个原组合单元、10条一周期通用性质通过SAT：max保持、不接新cmd、reset到0、合法递增、无事件保持、终止排空、不同tag排空、最终活动返回保持、正常合法接收、reset/abort屏蔽cfg及done。独立receiver从原JSON逐cell/pin核原D/Q、叶子、驱动完整性、无遗漏/环和来源SHA。原30门锥在固定ext_valid=1/state=0/link_take=0/reset=0/soft_abort=0下给出epoch=tag=max、take=0的实际反例。

这是抽象当前寄存器Q后的**一周期安全性质证明**，不等于整核可达性、不死锁/公平性、任意重排、多context或CDC证明。边界仿真补充真实完整消费者的执行路径，仍不扩大此形式验证边界。

## 同资源成本

|指标|原85|最终92|
|---|---:|---:|
|generic寄存器bit|4309|4309|
|映射DFF_X1|3823|3823|
|实际行为SRAM bit|131072|131072|
|矩阵/共享乘法器|8个S8＋1个S32|相同|
|映射cell总数|35422|35568|
|logic-only面积µm²|52415.566|52387.902|

同一Nangate45参考库、同一85映射配方；Liberty SHA 8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1，库存/面积由独立接收求和。最终面积差-27.664µm²（约-0.05278%）是重新映射后的cell组合差异；cell数增加146，不据此声称修复免费或带来可信物理收益。早期仅terminal修复map01为52441.900，最终cfg/done mask版map02为本表数据，不混用源码。

完整store82 wrapper不在logic-only面积中；外部恢复测试FIFO仍2槽，每槽128bit数据+32bittag，至少320bit加控制未进core。32bit tag线网/实际打包/布线代价没有计成零。此次RTL改变后不继承Issue86/88门级/STA资格，没有目标宏/PVT/布线、Fmax或总芯片PPA结论。

## 交付与后续

33个本任务Slurm均COMPLETED；其中原版本仿真退出1/SAT反例是预期缺陷见证，封装作业通过表示成功复现，不表示旧RTL通过。初版/正式运行、失败见证、负例和5phase来源均留档。完整96,406,212B/443成员在授权服务器，精选549,889B/158成员入仓，服务器两包、PC精选及5phase92条原Git源码字节全部核验通过。

统一[索引](../../project/experiments/epoch_boundary/results/issue-92/index.json)、[接收报告](../../project/experiments/epoch_boundary/results/issue-92/report.json)、[交接](../handoffs/2026-10-25-issue-92-epoch-boundary.md)。最小下一步由集成方沿新reset取消/终止排空合同接入共享V/S；如要发布92时序/门级资格，必须对92的实际网表另行执行，不能直接引用84/88。通用V/ROM整合、真实存储/互联/制造后定制、全模型数值与六类Block整机验收仍未完成。


发布回执（2026-10-25）：[PR96](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/96)已上传；Issue92为in_review，待独立审查/合并，未done。远端读回commit 66aa2795b4d03cc074f0df09396252c9b00d8f2a的报告、索引、接收报告均与原Git blob逐字节相同，详见work/Liangruizhi/92/remote-readback.json。后续文档提交不改冻结实验source。登记PR5 pending；看板board.json404且实际条目查询缺read:project，状态unverified、同步pending。审查人/管理员待指定。
