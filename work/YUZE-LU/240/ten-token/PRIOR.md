# Qwen2.5-3B：与用户已有 openTPU / LLAccel 实验对照及三轮改进

关联 Issue #240 / PR #241。此文件为先前独立实验的历史说明，后续十token研究见同目录RESULTS.md。文中“未上传”、本地路径和旧generated路径均是当时状态；其JSON已归档至evidence/prior-rounds，不代表当前PR发布状态。
基线源：PR241 e7aeed2097f57a5f910cae70eb51a220c49a8a14，model.cpp SHA-256 为
84aa752da4afaece43947f9ba86e2ab3665b5b8e72dc0a4bbca208b85cffd6e5。

## 先纠正比较对象

用户另一个侧聊确有完整真实权重的共同短测，不应继续引用旧的小模型公开表。
来源：../peer-systemc-20261109/结果报告.md、final-results.json 及其回收源码与 receipt。
Qwen2.5-3B、36层、H2048、FFN11008；Hello 提示词只有1 token，测位置1的一次有效 decode。

| 对方实测 | 设备 token/s | 资格 |
|---|---:|---|
| openTPU INT8 | 5.211746 | SystemC 包装的原生 RTL、真实权重/KV、全词表对 ISA 逐位相同；两步 HF 平均 cosine 0.985639，top1 2/2 |
| openTPU FP4，head INT8 | 8.840913 | 同样有真实 RTL/权重，但两步平均 cosine 0.774737、top1 1/2；不能当等精度 INT8 对照 |
| LLAccel 最快已完成配置 | 1.765797 | 原生整数/RTL执行相同；300MHz 条件；两步平均 cosine 0.245065、top1 0/2，模型质量不足 |

两种 peer 的频率在这次实验中也未独立物理闭合。LLAccel 不是比我们的架构预测快；它的约3.100GB/token搬运被默认100周期外存延迟、有限在途请求及SRAM等待拖慢。
LLAccel DRAM 模型与 openTPU LiteDRAM 模型不同；不能用这个结果给 ASIC 与 FPGA 下普遍结论。
本实验 decode2 是总上下文2的配置派生时序图，对齐工作量尺寸，但不是 Hello 的真实权重执行。
我们仍缺完整数值、真实KV、指令/RTL/物理资格，不能把预测速度当作已超过 LLAccel 的有效推理实测。

## 为何 openTPU 快

1. **片内数据路径。** 回收的 otpu_mxu.sv 明确由 DRAM 将权重送进预取 FIFO，与独立 ACT RAM 的驻留输入结合计算；不是每片权重都先写通用S再读回来。
   原 PR241 则将 DMA 写S、M读S放在同一个512位聚合端口日历上。读整片还要求连续占用端口，不能利用未来 DMA beat 之间的空隙。
2. **数据表示与驻留。** openTPU 的 qwen3.py 明确把矩阵激活动态量化为INT8，保留FP32残差、norm、RoPE及Softmax。
   我们采用S32激活/KV；FFN输入11008元素占44032字节，一个16KiB S装不下。重复A供数不会被更宽DP搜索自动消掉。
   量化到INT8后该向量是11008字节，但要另付scale、量化器和质量验证，不能直接修改dtype冒充等价。
3. **资源不同。** 用户 openTPU receipt 的 D128/ACT_ROWS16/ACT_BLOCKS128 对应262144字节ACT数据加16384字节scale；TMEM_WORDS65536对应262144字节逻辑TMEM。
   合计逻辑容量528KiB，尚不计实现复制、FIFO等；本模型激活的两个P加一个U仅48KiB私有S。不能据此推算芯片面积比例，但不能声称存储资源相同。
4. **调度范围。** PR241只有两个M在单个Dot内并行，外层run()逐算子等待；跨组结果仍经DRAM。F/G等五类分组能力没有被完整利用。
   这是架构研究模型，不是 #220 DP 生成程序的性能验收。当前差距不能归因于DP优劣。

## 实际改了什么

所有配置保持300MHz条件、W8静态矩阵权重、S32激活/KV、17.1GB/s两通道外存、32 beat/描述符credit。
仍是两个P和一个U，容量预算每组16KiB；没有提高外存带宽或降低数值位宽。

- 第一轮：当完整A放不下时保留可用前缀；按16元素分配相邻N8输出，合成64字节写回。
  输出窗口每行64字节明确计入预算，反过来限制K。每个输出在写ACK后标记，矩阵结束检查无遗漏/重复。
- 第二轮：S逐beat仲裁。M读取可穿插到DMA写的空隙；每个K8步骤等操作数到达才发射。
  最多每行64字节A staging和两个B chunk，总量不超过已预留的1024字节；换A行前等待旧MAC消费完成。
  整片依赖仍等待输入DMA ACK，没有凭空消除事务。
- 第三轮：把SiLU/RoPE/倒数微程序的最多16个packet上下文交错调度，消除每轮排空流水的气泡。
  保持E32四lane、II1、延迟6、同样微操作数；64种独立逐周期调度检查确认依赖间距和最终完成时间。
- 单独的硬件候选：DMA直接填M的两个B操作数银行，每个银行仍为单端口512位，接收和读取相互仲裁、释放后才重填。
  **这不是原S免费多端口。** 原来预算中的两个B缓冲迁到专用银行；合计容量仍受16KiB约束，但物理S/操作数存储划分、数据选择器、端口和控制必须重新实现。
  若保留完整现有16KiB S再额外加B银行，新增物理存储也必须另计，不能沿用这里的等总容量假设。

## 结果

以下全是SystemC架构时序预测。K512需扩展/核验命令与缓冲合同，不能算已经验收的K256硬件。

| 场景 | 原PR241基线 | 相同预算、K256仲裁/驻留/调度 | 加K512合同 | 单列B银行直送候选、K256 |
|---|---:|---:|---:|---:|
| 短上下文 decode，total context=2 | 3.0066 | 3.5312 | 3.6073 | 4.2978 |
| context512 decode | 2.7146 | 3.1383 | 3.1983 | 3.7401 |
| context2048 decode | 2.0957 | 未测 | 2.3804 | 2.6837 |
| B1/S2 prefill，2输入token | 2.8698 | 未测 | 3.0969 | 3.7419 |

单位token/s；prefill不能当decode。具体消融、停顿/搬运计数见 generated/results.json、round2.json、fixed-k.json、final.json。

- decode2：固定K256的吞吐提升17.45%；独立硬件候选提升42.95%。均不是 #220 DP 相对贪心的算法收益。
- decode512：固定K256的吞吐提升15.61%；独立硬件候选提升37.77%。均不是 #220 DP 相对贪心的算法收益。

第一轮context512：仅部分驻留2.7502，仅写回合并2.7316，合用2.7678；仅K512为2.8133，但K512再叠部分驻留和合并降为2.7666。
这组反例保留，说明需要联合选择K、驻留字节和输出窗口，不能只叠加优化开关。
第二轮K256逐beat、无其它新优化为3.0405；K256前缀/合并为3.0974；第三轮调度到3.1383。

## 剩余差距和实施顺序

即使B直送的短上下文预测4.2978，也仍低于openTPU INT8实测5.2117；没有达成“追平FPGA”。
context512最终B直送仍搬3.5191GB/token，平均约13.16GB/s。仅按当前流量除17.1GB/s，绝对上限约4.86token/s，计算/依赖只会更慢。
静态矩阵权重下界约3.086GB/token，仍有重复输入、KV与中间结果、未满beat等额外成本。

后续应按以下顺序进入正式PR，不能将模型候选直接写成硬件已实现：

1. 先落实同一量化合同的真实权重/KV图，完成与HF/整数oracle的比较。本研究W8没有完整质量验收，不允许换FP4或缩小执行范围来达标。
2. RTL任务落实beat级S仲裁、有限staging、packet上下文scoreboard、N8输出合并及背压/写确认；分别校准上述时间。K512单列合同与RTL测试。
3. B直送需单独硬件PR：冻结“DMA→哪个B银行→ready→消费→释放”合同，提交存储/端口/选择器面积、功能、随机背压与物理验收。不能通过M11/M12金属获得新有源逻辑。
4. 然后比较两种可付费的驻留方案：保持S32并给长FFN输入足够片内空间；或加入真正的INT8动态量化/scale服务并通过模型质量验收。两者的面积/功耗与精度分别计账。
5. 在图上进一步做跨算子分片与有限中间值驻留，避免当前全算子屏障及DRAM往返；输入驻留、partial accumulator、源释放、S存活和拓扑端点必须进入同一调度状态。
   此步骤才适合接入 #220 候选生成/状态转移并测DP收益，不能用本次硬件数据路径收益申领DP算法20%。

本地交付边界：没有改原工作树/PR；尚未发布硬件PR，未做新的RTL、全图数值、最终版图或能耗验收。
本目录保存可执行源码及证据，供主线程独立审查后纳入正式任务。

## 验证与复现

- GCC14.2.0、SystemC3.0.2，-std=c++17 -O2 -Wall -Wextra -Werror 编译通过。
- 原PR241 context512/context2048/prefill2三组基线所有既有结果字段精确相同；新增context2基线单列。
- 40个整模型/范围时序场景；40项独立分片数、矩阵工作、权重流量下界、容量/credit/时钟审计。
- 64种packet微操作调度检查；21项尾块、行切换、输出ACK覆盖和缺失生产者负向控制；原4项资源/KV ACK回归通过。
- 输出覆盖检查不计算张量数值，不能代替完整数值回放；外存模型未对DDR RTL/实机校准。
- 能量没有标定，本次不输出J/token或W。

在本目录运行（Python路径按本机安装调整；SystemC依赖见manifest）：

```powershell
python -B prepare.py
g++ -std=c++17 -O2 -Wall -Wextra -Werror model.cpp -I../side-systemc-block-study-20261109-02/deps/install/include -L../side-systemc-block-study-20261109-02/deps/install/lib -lsystemc -o model.exe
python -B run_ablation.py
python -B run_round2.py
python -B run_final.py
python -B -c "from run_round2 import run; import json; from pathlib import Path; rows=[run((w,'gap_packet_partial_coalesce_sched_k256')) for w in ['decode2','decode512']]; Path('generated/fixed-k.json').write_text(json.dumps(rows,indent=2))"
python -B check_changes.py
```

协作规则：rayggxia-project-collab 1.0.0；关联既有Issue240/PR241；本地实验交付、未在线提交；原项目管理检查PASS。
登记沿用既有management-hub PR5 pending；看板权限/配置本次未核验，未改变任务状态。下一位操作者先核对远端最新状态再移植修改。
