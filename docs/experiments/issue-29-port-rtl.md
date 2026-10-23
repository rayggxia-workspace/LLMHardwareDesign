# Issue29：有限缓冲RTL如何改变状态放置结论

更新：2026-10-23（UTC+08:00）。[Issue29](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/29)／[PR30](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/30)，负责人Liangruizhi。本阶段研究整体Goal仍active，尚无最终Block或端到端收益结论。

## 已完成的实验与正确解释

正式源码`916dcf9e74ecd6a2164bdbb79991b0f3f7ed1b1e`，tree `949a745e84fd65ba13188288a788aaeb05d74c37`。两个完整运行89836／89837自然COMPLETED0，分配8CPU；分别85／74秒是仿真工具运行时间，不是芯片性能。每次27种硬件配置、1872个可行程序、54组压力测试全部通过内部检查；1584个缺少静态连接的候选在生成阶段拒绝。两次27份results.json逐字节一致，包括全部任务时间、压力测试统计、模拟器二进制及保存的trace摘要。

真实执行的RTL只有两bank三端点控制器、端口仲裁、byte write、同址互斥和有限响应FIFO。每bank64KiB、beat64B；每端点FIFO深度1/2/4，1RW/1R1W/2RW是不同端口库存。M/V算术仍以Issue27的假设服务延迟模拟，scratch由静态容量约束表示，外存使用明确节流的流量源／接收端。没有实现矩阵乘、softmax、FP32运算或完整DMA／scratch RTL，不能把程序周期称为完整attention硬件或整模型周期。

测试程序使用Issue27实际观察的Qwen3 layer0/head0 prefill q32/k32/d128、decode q1/k48/d128形状，归档和shape均按SHA核验；payload是合成且带精确版本标记的数据，不是将模型真实张量放入算术RTL。原有真实数值证据仍属于Issue23/27。

## 关键结果：端口、调度和实现合同会改变收益

下表固定full六链路、无接收端停顿，每一方使用同样四种策略择优；所有FIFO深度在这组条件下结果相同。O/m/l全B0与全B1均使用相同硬件库存、流量和算法。

| 每bank端口 | phase | O/m/l=B0 | O/m/l=B1 | 已找到周期减少 |
| --- | --- | ---: | ---: | ---: |
| 1RW | prefill32 | 6977 | 6875 | 1.46% |
| 1RW | decode48 | 1983 | 1949 | 1.71% |
| 1R1W | prefill32 | 6843 | 6715 | 1.87% |
| 1R1W | decode48 | 1821 | 1819 | 0.11% |

本轮2RW各同硬件组中，八种placement的best-of-four周期相同。不同端口模式／队列深度不是免费改变，不能横跨这些组报告同面积加速。启发式不保证最优；critical策略的全部轨迹通过也不等于独立逐拍重审了所有最优策略轨迹。

Issue27的1RW对应差异约4.51%／3.92%，本轮缩小为1.46%／1.71%。原因不是单独添加某个延迟：本阶段改成逐beat轮询而非整burst占用、注册响应、完整ack依赖和明确接收端反压，是一个新的实现合同。这是对建模假设敏感性的证据，不能把两阶段绝对周期差当成某个单项优化的贡献。

720个删去未使用边后仍可行的匹配例，与full的完整result包括任务时间完全相同。删边不是有源重路由算法，不能宣称它提高了速度或已减少真实金属面积。所有54组静态选择目标中均找到同一个placement覆盖prefill/decode且达到两phase各自的最佳已找到值；full条件下111均满足。**本轮没有静态放置偏好冲突的证据，也不支持引入按phase动态重接线。**

## 实现成本与证据范围

行为SRAM共1048576bits；响应FIFO数据/tag/write合计1635×depth bits，指针／计数／RR控制位在depth1/2/4分别13/16/25bits。无隐藏请求FIFO或额外未记账read stage。上游持有请求、M/V scratch及算术属于测试平台／未实现部分，不能把本控制器寄存器总数当系统完整成本。`rsp_ready→req_ready`存在组合信用路径，协议是本实验自定义接口，未声称AXI。

- ModelSim ALTERA STARTER EDITION10.1d本机9组定向smoke通过：3端口×3深度，覆盖full+pop/push、registeredread、反压稳定、半双工、同址、部分字节写、复位保留SRAM、禁边与持续争用。
- Verilator5.042在ORFS26Q1容器运行，实际G++11.4.0；容器SHA256 `c742bf99ea498fb4da5135bc83fd1677abcebe0e64470e6a115f2baecb3905df`。版本显示UNKNOWN.REV，未编造源码commit。
- 独立全量结果审计1698897项检查通过，核验1872结果、345384依赖、22464计算区间、103896搬运区间及27组严格编译参数；24已保存program trace共122494cycle／1332transfer的最后ack与任务end对应。
- 独立逐拍审计：33份witness共2482636项检查、176981cycle、147868次accept与response相等；2737632个语义read bytes逐字节初始化／版本通过。2191项源码／bundle／结果绑定通过，8类真实轨迹变异全部被目标检查检出。7200B未知仅是decode未请求的尾拍padding，按实际case推导核验；首轮审计把padding误要求初始化的12个false FAIL保留，纠正检查口径后通过，未放宽语义数据规则。
- 保存的逐周期证据为24个program witness和9个stress witness，不是1872个程序的全部逐拍轨迹。best-of-four中的最佳策略不一定是这24份critical witness，不能扩大独立逐拍覆盖范围。
- 通用综合结构检查job89838已提交；当前仍在运行，尚未证明SRAM宏映射、实际面积、布线、时序、功率或算术RTL等价。即使通用综合通过也不能代替这些证据。

## 研究判断与下一步

可复查的候选单位是“计算事务＋必需状态＋端口／缓冲服务”，再由逐bank容量、共享资源争用、可行静态连接、真实电气／布线／时序约束筛选。当前只证明这些判据不可省略，还没有证明某个跨模型划分是最优或有充分收益。有限RTL后的收益较小，必须把后续重点放到能改变结论的完整权重/KV流量、投影/FFN、多头多层与差异架构，而不是继续增加同一小图的配置数量。

并行物理证据已更新至PR17@ce5896d：openTPU固定small／单typical／固定布局下，拆分相对合并叶面积+0.412%、线长+7.142%、通孔+2.974%，已形成合格成对工程结果。允许新增BUF/INV/CTS且完整父层路由的H1，不能当制造前冻结有源底座、产品确定后仅少量金属定制的H2，也不能校准本attention控制器。独立审计另发现三文本产物Git LF字节与生成时CRLF的manifest SHA不一致；数值复算通过，原字节校验缺项保留待处理，不能称全部证据完整。

## 成果位置与恢复

大体积原始证据已放获授权共同目录`/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-29/`，不是仅留本机：

- `formal-bundle01.zip`：源码及1872输入，SHA256 `5f95b9461565940dadf0bcfb4a9f4110d098c978c9cc338415b14ddebc0b0825`。
- `formal-results01.tar.gz`：20777230B，包含33个压缩trace，SHA256 `3281a07d8bbdb819bcd869afb8b2b3be0c507e8a90c3a6e7184529e6f4fd0e64`。
- `formal-results02.tar.gz`：1215519B，第二次结果／清单／编译日志，SHA256 `8d71566b9d74233a5c7c12cfbf47b5363b9ea85f75f0fa9fbd25dba8ff13017f`。第二次33个trace摘要在results内，原trace留本人formal02目录。

本人服务器原始目录`/public/home/yuzelu/RuizhiLiang/issue29-port-rtl-20261022/{formal01,formal02}`，本机完整包与审计在`D:/Projects/Codex/port-rtl-study-20261022/`。源码和正式命令见`project/experiments/port_rtl/`，独立工具和报告见`work/Liangruizhi/29/`。PR当前draft，Issue in_progress；登记pending、看板unverified／同步pending，审查人与管理员待指定。
