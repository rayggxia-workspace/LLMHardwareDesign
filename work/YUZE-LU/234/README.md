# Issue234：Qwen3B SystemC 时间、能量与充分优化对照

2026-11-09 CST，YUZE-LU，[Issue234](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/234)。
独立分支 task/234-systemc-benchmark，正式提交以已知main c4d7b960为底；老算法从375b8fca0/在线冻结1d284bdc只读核对。
不修改母聊天的算法工作树、活动分支或作业。

任务未完成。不得将已有B1/S2无KV模型代价换算、单宏资格或下面的合成测试宣称为整网SystemC/焦耳验收。
用户要求持续多轮直至达到经核对的FPGA门槛；初始主场景拟Qwen2.5-3B B1、输入512、decode128，补128/2048上下文。
用户已确认生成速度和每token能耗均须达标，仅公开benchmark，无板卡要求；对照用平台原生充分优化配置，不强制退到我方标量布局/数值格式。
2026-11-09用户进一步确认先固定九组资源（3M）和现有外存预算，优化后再评估扩容，见[资源约束](resource-policy-001.json)。

## 交付顺序与硬门

### 2026-11-09 13:22 CST：程序级SystemC与数值矩阵

[真实局控程序](n-exp-lc-result-001.json)：E13/S/N Stats2/Exp1经真实compact64母控/局控镜像运行，
11输入×2背压×3初态×RTL/U64父层最终网表，原生132次、真正SystemC内核再132次，数值/镜像/时间一致。
完整[x,0]由现有E13经S产生，无服务间补数据；读80B/写64B/两次stored ACK、四类损坏镜像拒绝均检查。
无/有背压窗口1.300/1.370us含行为PM与控制，不能作通用Exp系数/整网时间。810文件7.769MB全部成员及远端SHA核验。
首次SystemC驱动未处理Verilog finish而触发watchdog，完整留档，仅修C++驱动，无硬件修改。

[数值矩阵](recipe-matrix-result-001.json)：101543 COMPLETED0:0/15m40s，单节点6×10。
P128/P512 prefill、P512单步decode，RMS1/2+门乘细6位的18样本logits/.02/argmax及72KV全部通过。
数值配方修复不计DP收益；decode仍用HF量化past，不是连续D128。先前FP32导图严格门仍false，未覆盖或抹掉。
42文件2.515MB已全部SHA回收。连续生成驱动已接配方与resume身份，D128六场景脚本待冻结提交，实际执行看后续部署回执。

41项单位检查、结构、语法和diff通过；首次默认TEMP沙箱权限错误6项，使用任务自有TEMP重跑，无断言删改。
固定九组/3M/位宽/原预算；完整3B D128、整网SystemC token/s/总J/token及FPGA双门仍未完成。
下一步是整数KV连续回放与模型组装；缺失能量不填零。登记PR5 pending，看板unverified/同步pending，沿用Issue7交接。
Issue234 in_progress，PR235 draft，审查待指定，不自审/自合并。

1. 冻结旧算法、硬件、权重、任务范围和同前缀数值参考；旧B1/S2保留为回归，补实际带KV编译和生成。
2. 复用#145/#153/#197合法来源：七宏无时钟功能模型不能直接提供周期；时序接入实际叶/局控/DMA校准。
3. SystemC事件推进实际资源、S窗口、队列、信用、存储bank、确认；真实命令/搬运事件与压缩循环具有来源及等价检查。
   不以旧计划的start/end或makespan驱动结果；压缩加速必须保留相互作用，不能删真实通信等待。
4. 命令/存储/互联/时钟/控制/泄漏能量分项；逐一绑定活动、库、PVT与外存器件。未知系数保留缺项，不填零。
5. 以同模型/同输入/质量门比较prefill、TTFT、decode token/s、J/token，能量计入边界和不确定性相同或分列。
   不同checkpoint只作为各自平台事实，不据参数数量相近作通过判定。
6. 每轮分离算法、配方与硬件变化，记录占用/等待/带宽/流量/活动；对照充分搜索tile/量化/并行/流水/驻留参数。
   不能证明全局最优时记录最佳合法配置、搜索预算/收敛，禁止伪称最优。
7. 落后先排仿真误差/映射/软件缺口；只有定位到真实硬件限制并有反事实实验后另开硬件Issue/PR，不覆盖旧验收。

## 已核对的复用来源

- 七宏SystemC：本地Issue145 main整合41af0f188，3.0.1；原模型无时钟，E op13和R控制接入有版本限制。
- #197/#198已有整模型SystemC/行为外存，不能继承尚未校准的全芯片周期/器件能耗。
- 服务器SystemC3.0.1库：`/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153/install/lib64/libsystemc.so.3.0.1`。
- llaccel本地参考服务器commit f7db8a22791a1ce9dc13e7c90b0b9b9386169aa5；其44个Llama/Qwen测试明确是小随机模型，不能冒充预训练3B性能。
- openTPU参考服务器commit f237dab2f196855a59a083b1454786df8f01291f；官方当前README还报告原生优化和3–4B支持，需固定上游版本后复现，不能仅取旧较弱配置。
  官方入口 https://github.com/FeSens/openTPU ，板上监控含功耗/带宽，但当前尚无本任务板卡测量。

## 第一轮基础

`project/experiments/systemc_benchmark/timed_resources.cpp` 使用真实SystemC动态进程，从依赖和资源完成事件求开始时间；
测试串行、并行、端口争用、写确认依赖、fork/join和未知能量。当前资源容量为1，TSV时间ps、已知活动能量nJ；
没有泄漏/时钟/外存器件校准，不能声称总能量。`acceptance.py`独立拒绝缺失能量、不同工作负载或弱化对手造成的伪达标。

远端独立目录 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark/`。
probe-001/100664为单节点c64、6×10、60核，因SystemC3.0.1废弃SC_HAS_PROCESS且-Werror而失败；保留日志。
已删除过时API而非关闭-Werror；probe-002/100665因服务器Python3.6不支持capture_output失败，保留原件。
改用等价的stdout/stderr PIPE及universal_newlines，probe-003/100675实际COMPLETED 0:0；六个SystemC基础场景全部通过。
probe-result.json原件已回收，与服务器output.sha256的070253396dd4ad5bbe7b7bb90797d88f8d280cd9dcdf27865286f7b37f0eeae8一致。
本地两个验收门测试通过。合成测试不是Qwen3B/能量结果。

2026-11-09：核对官方README的3–4B板上性能及board.md。不能把旧100MHz构建的低可信度8.75–9.70W功耗估计与新133.33MHz构建的吞吐相乘当J/token。
SmolLM3-3B/ Phi-4-mini板上数字只作对应模型的原生参考；正式门须同checkpoint/输入/质量，不得直接替换成Qwen2.5-3B成绩。
用户已收到主场景/门槛选择与板卡/Vivado/功耗数据路径的异步问题，尚未收到回答；独立准备工作继续。

每轮完整计算使用单节点8×12或6×10，限制工具/BLAS线程；不操作其他任务。
项目结构检查通过。PR未创建，整网仿真/功耗校准/ASIC与FPGA适配/多轮优化均未完成。
登记沿用management-hub PR5 pending；未见board.json，Projects状态unverified/同步pending，待有权限维护者。

## 2026-11-09 CST：已执行的下一轮及待执行项

源码入口及复现说明见[systemc_benchmark](../../../../project/experiments/systemc_benchmark/README.md)。
当前仍未得到合格的整模型decode token/s、J/token，也没有通过FPGA门槛。

| 作业/环境 | 实际证据 | 边界 |
| --- | --- | --- |
| baseline-001 / 100678，COMPLETED 0:0 | 六个旧计划在真正SystemC中执行，独立重算旧成本；见baseline-result.json | B1/S2、无KV，旧保守整核锁资源模型，非校准芯片时间 |
| reference-001 / 100679，COMPLETED 0:0 | 六个小上下文完整36层HF缓存/完整前缀对照 | FP32数值参考，非硬件时延 |
| reference-002 / 100686，COMPLETED 0:0 | P128/512/2048、各两提示、输出128，缓存对照通过 | 128个生成token含首个prefill输出，另执行128个cached calls；标准生成128仅需127个cached calls |
| power-001 / 100719 | 01:16 CST仍PENDING(debug/Resources)，单节点6×10 | full ODB/SPEF及原始库的工具库存，不加载VCD，默认活动功耗不合格 |
| export-001 / 100726 | 同时仍PENDING(debug/Priority)，单节点6×10 | 显式72路KV ONNX导出/数值实验，尚无成功回执 |
| m-activity-001 / 100734 | 同时仍PENDING(debug/Priority)，单节点6×10 | 真实旧整数操作数、RTL/最终网表/VCD校准，尚无成功回执 |
| 本地隔离WSL22 | 真实SystemC3.0.1六场景通过；M72个原生运算RTL精确S64通过、Execute均22拍 | 同版本工具/库独立副本，2核；最终M网表正在编译，不代表功耗校准已完成 |

后三个作业最初c64/c96无时限，因预计等待数天，显式改debug/30分钟，资源仍单节点6×10。
保留每次提交源快照，未改运行中的attempt。01:16队列预计01:23:35、01:53、02:23开始；预报不是实际开始/成功。
本地WSL无全局软件安装，无修改WSL内存配置；使用本人任务目录、原库/工具的可移植副本。
OpenROAD无法打开中文路径，原本地001/002失败；003经ASCII符号链接读完整M ODB/SPEF成功。
其默认活动0.187W约值未加载VCD，明确不用于J/token。WSL临时目录不持久，现使用私有home目录继续。

回收包foundation-results-001.tar.gz SHA256：
`80a734e1a872c5b70344dccc3064a68c65cf0030d897646fcf09b3f21216f7ad`。
包含baseline/reference原回执、日志、TSV、token及logits；大文件留raw（忽略）及远端任务目录。
reference-result.json为这些独立回执的摘要，host_wall_seconds不得作为硬件时间。

工具副本portable-tools.tar SHA256
`8099729232c20bf991ef6b0b353ff328a27cb5e9eae1bf5da938513238af8daa`；
portable-verilator-systemc.tar SHA256
`020da6b717ab61669bb4f8d00ecaab04a467acd40ee6485a3d6a18afc8113ad7`。
OpenROAD build版本字符串unknown，绑定其二进制SHA/manifest；Yosys0.68、Verilator5.042、SystemC3.0.1。
本地只为捕获首个投影制作44行embedding+完整norm/qproj的有界输入包，不是整模型：
capture-inputs-001.tar SHA256 `ea1ecf3487c3602f05e51d65c65902c454559e5f6f45946737b423886749eec9`。

### 已冻结的对照源与差距

- openTPU `91df41092f612361c5bc22f83b31d23382ffabb0`，官方codeload归档SHA
  `f19d9008123ccab2ad9363c9bed067c8a0a372433e60a0b1cf1584cf33bdac67`。
  这是较新源，不以旧参考快照代替。官方SmolLM3-3B、Phi4-mini、Qwen3.5-4B板上结果
  不能直接当Qwen2.5成绩；Qwen2/bias前端当前不支持。需真实适配或共同checkpoint。
  未取得同构建实测功率；旧board.md默认切换功耗不合格。
- llaccel `f7db8a22791a1ce9dc13e7c90b0b9b9386169aa5`，本人任务目录源归档SHA
  `adcd838ba8329329c146cd9f42a2c5fb9c5562c63cb253ca0d8b6cf44ee53b1b`。
  原生编译需要MLIR/LLVM23等环境；现有随机小模型验证、3ns约束不能当完整3B已达频ASIC证据。
  本任务尚未完成3B原生编译、PPA、功耗或配置搜索。

### 接下来必须补齐

1. 带KV导图、状态数值和整数设备程序；旧S2无KV成本不可外推成decode。
2. M/E/G/N/S和局控/母控/真实DMA/互联的活动、等待及队列校准，器件外存与容量资格。
3. SystemC按实际事件推进，整模型延迟与能量组件完整、误差和不确定性公开。
4. 对照同checkpoint/输入/质量的充分适配与搜索预算，分别报告平台资源及能量边界。
5. 分离算法/配方/硬件的多轮改进；证实硬件限制后独立Issue/PR。当前未因旧标量配方低利用率而武断判硬件失败。

`energy.py`只提供能量积分：idle含局部时钟/泄漏，active按减去同窗idle后的增量累计；未知部件总量null。
`acceptance.py`仅元数据初筛，不能用填true/填SHA取代独立证据检查。登记/看板原缺项保留。


### 后续实际回执（2026-11-09 01:33 CST）

- 100719最终COMPLETED 0:0、47秒。六套完整物理视图/原始库均完成；回收power-results-001.tar.gz
  SHA256 `ee76935c101393fbfcbf63c0441824ddecd15796f53fc6718084144fbda3e83a`；六份日志SHA及本地M四文件逐一对上。
  [库存回执](power-inventory-result.json)全部保留workload_energy_qualified=false。
- 100726最终FAILED 1:0、90秒。五个形状通过，prefix=2/query=1在ORT与HF的logits比较失败：
  103/151936元素不满足既定atol=rtol=5e-4，违例最大绝对差0.00091636。保留失败，不放宽阈值。
  新export-002冻结源SHA `8ce3ea1c30fdbad0c9737290105c859b3d36c087bd4ab68eac93e998e8577364`，
  默认禁用ORT图融合以诊断数值变化，补ORT argmax和输出数量检查；提交100766，单节点6×10/debug，尚排队。
- 100734在01:31 CST仍运行，仅本任务M活动实验。其trace99版本源保持不变。
- [M实际RTL回执](m-rtl-result.json)：72个真实操作数部分积均精确、Execute22拍；不是整模型数值/时间/能量。
  私有本地001/002编译因Verilator把split文件重新按-j聚合而缓慢，记录后仅终止该两处本人构建；
  003用--output-groups 0和flat网表顶层net trace重试。此为主机工具效率调整，不计算为设备或算法收益。
- llaccel所需LLVM23.1.1官方Linux包调查中：服务器直接下载网络超时，改从本机HTTPS获取至任务raw目录。
  未执行/未验签/未完成peer编译；不降低原生工具或功能来制造对照。

### 活动校准与原生对照（2026-11-09 03:05 CST）

[Draft PR235](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/235)，任务仍 in_progress。
尚无合格整网 decode token/s、J/token 或 FPGA 达标证据。

- 100734 最终 COMPLETED 0:0（14m07s）；最终网表与 RTL 的72个真实部分积精确、Execute22拍。
  原功耗日志实际注入0个pin，全部作废，保留错误日志与原VCD。修正scope为`dut/block_v2_m`，
  仅平移VCD起点，不改值/事件次序，现有631740个pin获得真实活动。
  剩余732个由OpenDB逐项确认全为ANTENNA_X1/A，原Liberty自身internal/leakage表均为0；
  输入负载仍在原ODB/SPEF中。[分类证据](m-activity-classification.json)。
- [连续累加](m-streams-result-002.json)：三输入各取第0/7列，实际累加到K1000后测量16K、48个分量。
  六对active/同末态idle均通过独立Python S32重构与S64核对，每分量27拍、Execute22拍，
  增量约0.166–0.172 nJ/分量。不是完整Dot/整网能量系数。
- [原生打包](m-tiles-result-003.json)：真实K32/N8，三个输入各173拍，Execute49/49/49，
  扣同末态idle后的增量5.845/5.895/6.351 nJ。
- [精确修正位优化](m-tiles-result-004.json)：第三分量严格0或1，使用已有S8输入模式；
  无需改变硬件、量化精度或DP。三例均149拍、Execute49/49/25，增量5.301/5.390/5.753 nJ。
  173→149仅使该命令体耗时降13.87%、吞吐增16.11%，不计作DP收益或整模型加速20%。
  两组窗口包含M引脚B/A装载、Scale/Execute，**不含S32分解、真实S feeder、最终ReadRaw、
  局控取指/发令、写S确认、DMA/互联**。目前验证服务/活动，尚未成为完整生成程序。
- 原始source/operand/VCD/功能与功耗日志已存本人远端任务目录并回读SHA：
  [003归档](m-calibration-archive-003.json)、[004归档](m-tiles-archive-004.json)。
  零延迟VCD缺毛刺、样本及其他组件覆盖不足等限制保留。
  [Q投影工作量下界](q-projection-work-bound.json)仅约束冻结标量配方，不是SystemC decode成绩或硬件根本下界。

对照保持原生能力：

- openTPU隔离overlay接入真实Q/K/V bias，覆盖单步、rows、tiled投影，保留原量化、KV和调度路径。
  本地独立测试发现并修复新HF的`rope_parameters`配置差异和列bias广播错误，失败输入/日志保留。
- [六个小模型回执](opentpu-qwen2-smoke-result.json)：三seed×int8/fp4，非零bias、GQA8，
  与HF独立参考、原生量化仿真器交叉核对，resident decode及prefill通过。
  仅约318万参数，非3B数值证据；fp4跟量化仿真一致不等于HF质量相同，余弦/argmax差异保留。
- 使用`target.config('ypcb-00338:m4')`，不用会关闭可选ISA特性的`board_config()`默认值。
  原生4GiB、PAIR/DSTEP/STREAM/SEQ_WC均启用；最终仍需核对这一版本实际PPA及频率。
  旧co-sim便捷函数2GiB上限会排除合法3B int8，因此不把它当真实板卡能力。
- [完整模型编译](opentpu-full-compile-result.json)：36层/H2048/V151936未缩小，三上下文×两格式；
  int8图像3.16–3.21GB，fp4图像1.85–1.90GB，均在4GiB内。
  以HF oracle的真实首个生成token定位embedding，现为编译证据，不是权重数值/周期/能量资格。

最新尝试均单节点6×10/debug、30分钟，没有修改其他任务：

| 尝试/作业 | 实际状态与范围 |
|---|---|
| export-002 / 100766 | FAILED 1:0，73秒；禁融合后P0Q1的一处logit、P2Q1两处KV仍超过原阈值，保留失败。 |
| toolchain-001 / 100826 | FAILED 1:0，3m02s；clang/clang++/MLIR/llvm-config正常，generic `lld --version`按工具设计返回1；并非所有工具不可用，llaccel仍未编译。 |
| export-003 / 100831 | FAILED 1:0，70秒；静态mask/positions常量已烘入，四形状通过，P0Q1一处logit、P2Q1两层KV仍超5e-4阈值；三样本完整诊断保留。 |
| opentpu-001 | sbatch因CRLF拒绝，没有job；源和错误保留，后续SBATCH归档写LF。 |
| opentpu-002 / 100852 | 核对属于本人且仍PENDING后取消；本地已定位theta/bias接入错误，避免跑已知错误源。 |
| opentpu-003 / 100883 | PENDING；完整3B六配置，原生RTL+LiteDRAM周期实验。零数据只用于dense时序，不作质量/能量证据。 |

本地仅任务raw/私有WSL工具副本。Windows原Torch2.4与现Transformers不兼容，
从官方CPU索引取得Torch2.10私有wheel，未安装/改写全局包，版本/SHA保留。
M完整descriptor网格8192种×三初态通过，三份周期表SHA完全一致，见[m-profile结果](m-profile-result-002.json)及[归档回执](m-profile-archive-002.json)。这是独立M及重复输入行的形状/握手验证，非完整模型数值、S/LC/DMA或能量。
下一步为真实KV整数程序、SystemC全组件校准、完整peer周期/权重质量和能量边界。
公开低置信度默认活动功率不能用于板级J/token通过判定。用户已确认：公开benchmark即可，无板卡复现要求；生成速度与每token能耗均须达标，约10 token/s只是预期。完整[比较合同](BENCHMARK_CONTRACT.md)和[来源/数值/SHA](public-benchmarks-001.json)已补齐。公开更强的3B FPGA结果必须保留，不靠选择较慢对手通关。

2026-11-09 03:25 CST：100883仍PENDING(Resources)，未把排队写成周期实验通过；[显式KV第三轮摘要](export-result-003.json)保留失败。

## 驻留连续发令诊断

[归档](m-saturation-archive-002.json)：1024个S8 K32/N8 Execute，ready恒1、下一命令预先有效；三初态均16拍接收间隔、最终S64正确。不含装载、读回、S/LC/DMA。第一轮驱动未设b_half导致B拒收，修正并保留失败，非硬件故障。

[完整线性工作量预算](linear-capacity-result-002.json)：含36层所有投影和LM head，共3,085,697,024 MAC/token。授予保持质量的S8、完美分配和全部非M开销为零，三M/300MHz的标准直接GEMV路径上限约4.66669 token/s。这不是SystemC整网成绩或任意算法的数学下界。已单独建[Issue238](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/238)处理短K发令/排空/提交瓶颈；不把改硬件或改精度计作DP收益。


## 2026-11-09 04:10 CST：硬件分离与peer仿真限制

- [硬件草稿PR239](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/239) / Issue238独立处理长K候选，保留原M。RTL驻留吞吐不是算法或整网收益。
- 100883最终FAILED 1:0、30秒，完整六配置均在Verilator展开4GiB DRAM的单数组范围上限失败；尚无peer周期。
- 仿真存储改为四段，保留4GiB及所有控制器/时钟/带宽逻辑。1024词实际RTL检查逻辑文件加载、双通道散布、逐词/跨分段写入通过，见[回执](peer-memory-equivalence-001.json)。原生lbeat位宽警告保留，与原模型一致，非放宽功能比较。
- 新opentpu-004 / 100950，单节点6×10/debug 30分钟。源归档SHA b7471c269ff83823b39972b09cbcd1e07f1a6456aa7f1001230ec101b270afc3。此时仅提交成功，周期/数值/能量未通过。


## 2026-11-09 04:38 CST：KV入口及E活动校准进行中

- cached-integer-001 / 100968仍PENDING，单节点6×10/debug，源包SHA 8ac987008237d8f46b6a05517693af2830040251717d2cde3b29d6b1126f814f。三样本×六个既有导图形状，输入KV来自HF并显式量化，拟检查logits及72个K/V。未当作连续整数KV、完整主场景或SystemC成绩。见[campaign回执](cached-integer-attempt-001.json)。
- 新增运行时S32状态合同、精确Neg降解；旧程序默认分支在独立小图中指令和数值不变。主机模拟按最后使用回收对象，不改变设备存储/搬运。仅对能证明二进制64精确的整数点积使用BLAS，否则分解并证明或回退整数，Python任意精度交叉核对。此为主机验证提速，不计设备或DP收益。17项基础/状态/参考数学检查通过，不能替代完整3B验证。较新主机改动尚不在100968冻结源中。
- 紧凑E Min/Select的RTL三初态、活动/同末态idle窗口通过，串行服务分别6/7拍，每窗512命令。第一次本地路径拼写错误被驱动拒绝，保留后改正；不是电路失败。[RTL回执](e-rtl-probe-001.json)。e-activity-001 /100991仍PENDING，单节点6×10，源包SHA e968834c91b84912da074fed95ac78985d4f9213e622aed135b95d03fd8d2fea；真实网表/RC功耗还未跑完，不能计成已校准E能量。
- [带宽条件预算](memory-budget-001.json)对声明1MiB永久权重缓存、B1密集流式GEMV计算；到10 token/s，仅权重读的旧128bit标量记录约494GB/s，假设打包S16约61.7GB/s。这是假设化交通下界，未认定外存接口、质量、压缩/打包或SystemC达标。
- 硬件PR239全位宽补测：K256/N8的S8×S8=44拍，混合S8/S16=108拍，S16×S16=300拍。旧S32×S16需多分量，不用44拍冒充其实际成本。当前所有整网速度/总能量/FPGA门槛仍未完成。

调度回执：仅在核对本人三个任务的WorkDir、PENDING、单节点6×10后，将候选分区拓宽至c64,c96,debug；先给100968/100991加afterany前置依赖，再拓宽100950分区，确保本活动最多一个作业在运行。没有修改/借用他人作业。[实际回读](resource-update-001.json)。首轮保护检查因Slurm将待调度节点数显示为1-1而拒绝，未改作业；修正解析后才执行。

## 2026-11-09 05:08 CST：真实peer周期与连续KV入口准备

- 100950已实际RUNNING；三个FP4配置结束各自单步RTL：P128为15,143,569拍、P512为15,295,910拍、P2048为15,864,296拍，在声明133.33MHz下分别8.8044/8.7167/8.4044 token/s。[部分结果](opentpu-partial-004.json)。此时三个int8仍运行，作业未终态，不写整批通过。零数据、无完整权重质量及能量。
- 原生路径审计：`compile_step()`、`compile_decode()`和`compile_generate()`复用`qwen3_step`计算核；当前试验仍缺常驻生成循环、采样/argmax及主机路径，不能把单步结果乘128冒充充分优化的整请求。公开生产配置成绩仍独立保留。
- 新动态KV模板的小型2层模型在长度2/3/7的FP32动态执行及专化后均与独立HF核对通过，[工具/输入/输出散列](cached-template-tiny-001.json)。真实参数保持图输入，不把实时KV烘成权重；固定位置才折叠mask与RoPE。当前是主机导图优化，不计作设备或DP收益。
- 新`kv_handoff.py`要求所有层的S32整数输出直接交给下一程序；缺层、长度/格式/范围错误或非运行时合同均拒绝，禁止悄悄替换为HF状态。20项单位检查通过；尚无完整3B连续状态链，不能以这些检查替代。
- 新frontend-full-001 /101035，六个完整3B形状：P0/Q128、P0/Q512、P0/Q2048及P128/512/2048的Q1；包含最新主机整数回放与完整模型模板核对。源包SHA 780a9eaf5d4a77d5700d005d50811054572238c62e8315ddaae24a4f1b98ebed。[提交回执](frontend-full-attempt-001.json)。实读单节点6×10、PENDING、afterany:100991，因此整个活动仍至多一个远程作业运行。尚无该批结果，不当作完整生成/SystemC/能量资格。
- 本地依赖只解包到任务raw与本人WSL任务目录；Windows无onnxsim对应wheel，源码包因Windows长路径安装失败，未改系统配置/全局包。改用同版本Linux wheel在私有目录完成专化，失败日志保留。

整网SystemC decode速度、总能量与双门槛仍未完成。继续等待数值/活动结果，按实际失败修正；不因peer单步接近10而宣称本方达标。

## 2026-11-09 05:48 CST：整数状态链及两种S校准

- 100950最终COMPLETED 0:0，26m18s，六组原生RTL/LiteDRAM单步结束。
  P128/P512/P2048：FP4为8.8044/8.7167/8.4044，INT8为5.1993/5.1736/5.0572 token/s，
  声明133.33MHz。仍是零数据时序诊断，非完整权重质量、常驻生成或能量资格。
  [完整回执](opentpu-result-004.json)的60,142字节原始归档已回收，30个清单文件逐项SHA一致。
- [小模型空缓存整数链](tiny-chain-result-003.json)：两层、两token整数prefill→三个连续整数decode，
  所有KV均来自实际整数程序。四检查点logits和四KV的相对L2均≤0.000151，argmax一致。
  三个独立校准输入与评估输入分开。KV统一尺度通过显式Convert指令实现，无隐藏HF替换或缩放；
  不能称为完整3B、设备时间或能量。初次prefill校准遇到causal mask的-inf而失败，保留002日志；
  003按主入口相同规则仅观察有限值、拒绝NaN/+inf，未放宽质量阈值。完整源快照与结果归档SHA保留。
- 100968最终FAILED 1:0，32秒，六个worker均在导入时缺libssl.so.1.1，尚未执行模型。
  仅读取宿主原库，复制到本任务私有python-compat-001，SHA逐项一致；容器实测导入
  OpenSSL1.1.1k、Torch2.10cpu和Transformers5.20.2通过，未改共享环境。
  101035核对属于本任务且PENDING后取消，防止同一已知启动故障，未取消他人作业。
- [101203重试](cached-integer-attempt-002.json)等待100991，带主机精确Dot与旧adapter逐位对照；
  [101211完整形状重试](frontend-full-attempt-002.json)等待101203，含小图整数prefill链和HF实现源SHA；
  原失败与各自冻结源版本保留，不能将最新代码套入旧回执。
- [局部S RTL实测](s-rtl-result-001.json)：两种S×读/写/混合×三初态均通过独立数组、背压和同末态检查。
  串行请求到响应消费均3拍，非流水吞吐结论；窗口包含518命令。使用明确零延迟功能银行视图，
  原银行任意#DELAY不冒充300MHz表征。[101227](s-activity-attempt-001.json)等待101211，
  校准两种真实S网表、原SRAM库及提取RC；feeder活动另验。
- 21项单位检查、管理结构与diff检查通过。上述远端均单节点6×10，按afterany串行，
  05:48实读100991已RUNNING，其余依赖排队。完整3B连续KV、SystemC整网时间、总J/token及双门槛仍未完成。

回执：rayggxia-project-collab1.0.0；Issue234/草稿PR235，负责人YUZE-LU；登记PR5 pending，
缺board配置/Projects条目能力，看板unverified、同步pending，沿用Issue7交接；不自审/自合并。


## 2026-11-09 06:42 CST：拒绝浅层功耗结果、N原生命令校准和3B误差定位

- [101203实际结果](cached-integer-result-002.json)：FAILED 1:0、5m40s。六个完整36层小形状中，
  P0Q1/P0Q2的部分V状态超过原2%相对L2阈值；P1/2/16/32的Q1通过。18份logits均低于0.009、
  argmax相同，且所有输出逐位等于主机提速前adapter，但不能据此把失败KV判通过。
  41个原始清单文件回收SHA一致，失败与源版本保留；带HF初始KV的单步不能代替连续整数生成。
- [E最初功耗](e-activity-result-001.json)只注入273个pin，虽然100991 COMPLETED且功能正确，
  其功耗系数已明确拒绝。[修正后六组](e-activity-result-003.json)深度2、仅转义STA名称中的字面反斜线，
  168539个pin有效注入，141个剩余pin全部按ODB和原Lib核为自身功耗零的ANTENNA_X1/A，输入负载保留。
  所有24份VCD头一致、三初态数值/周期与原结果完全相同。Min/Select增量约23/26pJ；
  仍为采样、零延迟无毛刺，不是完整E trace或整机J/token。160文件本地核验及远端归档SHA通过。
- [N采样](n-activity-result-001.json)：三组RMS24/L2标量/相对Exp标量，RTL与最终网表三初态、
  背压和独立整数参考均通过。每服务268/110/12拍；172438 pin有活动，300个剩余pin均按原库/ODB核为
  天线二极管，负载保留。18份功率报告和54份相同VCD头核对，324文件归档本地/远端SHA一致。
  这些不是任意向量长度或全部N负载分布的能耗资格。
- [N降解反例](n-native-gap-001.json)：冻结streaming_ir的NExp统计count=1，实际相对max(x,0)
  的oracle/原生服务需要count=2与[x,0]。仅把已验证驱动改回count1，接受网表上即复现负输入数值失败。
  两者Stats均4拍，说明周期相同不代表语义相同；属于编译模板合同问题，未推断硬件缺陷。
  父任务/冻结源保持原样，后续本任务后端须显式使用正确序列。
- 101227核对本人PENDING及WorkDir后取消，避免浅层VCD重复故障；[101347](s-activity-attempt-002.json)
  以深度2、STA名称转义和99%覆盖筛选重新冻结，等待101211。
  [101479归因实验](cached-integer-attempt-003.json)等待101347，区分S16权重量化与整数运算误差，
  原HF阈值不变，不用FP32替换整数输出。均单节点6×10，依赖链至多一个本任务远程作业运行。
- 22项单位检查及管理结构检查通过。06:36实际101211仍PENDING(Resources)，101347/101479等待依赖；
  排队不是实验通过。完整3B连续生成、已校准SystemC整网token/s与总J/token及双指标达标仍未完成。

下一步：完成主场景数值/模板与S活动，修正具体误差并接完整整数KV序列；将N原生合同修正纳入本任务
SystemC后端，继续补LC/MC/互联/时钟/外存。所有硬件/精度/配方变化单列，不计为DP算法收益。

## 2026-11-09 07:39 CST：完整形状失败保留、S活动结束和自由生成入口

- [101211终态](frontend-full-result-002.json)：FAILED 1:0、16m23s。
  完整3B动态模板及专化通过，不能替代整数验收。P128/P512的Q1整数三样本通过；
  空缓存P128/P512部分KV超过原2%阈值，P128有一个logits argmax不一致；
  P0Q2048及P2048Q1分别在v182/v187被原S64部分和上界拒绝。124个归档文件回收SHA一致。
- 新增整数L1收缩上界，先证明uint64范数求和不溢出，再约束所有原生分量部分积；
  独立Python任意精度验证长稀疏收缩及溢出反例。不移除S64检查、不改变运算或计为DP收益。
  [101480](cached-integer-full-attempt-003.json)用六种完整形状检查新证明，同时区分
  S16反量化FP32/HF误差与整数/反量化FP32误差；101479仍为小形状归因实验。
- [101347 S活动](s-activity-result-002.json)：COMPLETED 0:0、1m09s。
  两种16KiB S的读/写/混合、RTL及门级三初态通过，普通串行服务3拍；
  base/P有效pin为17309/47623，143/178剩余pin按ODB/原库分类为天线二极管。
  原SRAM Liberty、提取RC和完整银行pin活动保留。用纯读/纯写预测混合访问的增量误差
  分别3.888%/10.270%，没有事后放宽阈值当作精确通用系数；feeder尚未覆盖。
- [RMS2048 N采样](n-activity-result-002.json)：真实2048元素统计/Finalize/ReadFactor，
  三组捕获衍生数据，RTL/接受网表三初态、独立整数平方根和oracle一致，每服务8364拍。
  增量约47.95/48.66/48.48nJ，持续idle另计。VCD完整定义头与既有N审计一致，
  172438有效pin及300天线二极管分类可追溯复用。两次主机分析进程SIGSEGV在调用功耗工具前失败，
  原日志和部分VCD保留；串行重试成功，原因未证实，未将重试参数称为已证明修复。
  106文件、1.516GB原始归档逐文件及本地/远端包SHA核对；仍非整片能耗。
- [自由生成入口与重启证明](sequence-tiny-result-003.json)：tiny两层102912参数，
  真正由整数logits选出231/127/225/127，第一段两token、恢复两token与连续四token的最终四个KV
  逐位一致，handoff记录相同，所有HF检查通过，最大相对L2约0.000136。
  新checkpoint/原始S16参数SHA及源版本/状态/校准身份检查已纳入；150文件归档本地/远端SHA一致。
  [旧入口冻结记录](sequence-tiny-result-001.json)保留，不用新源替代旧证据。
- [101486](sequence-attempt-001.json)：完整3B六组自然提示P128/512/2048×两提示，先请求首token，
  完整目标D128。先有整数prefill，再允许整数KV继续；HF输出不注入现场状态。
  单节点6×10，afterany:101480；两组大prefill仅在主机校准阶段互斥，避免同时保留大型观察图。
  07:32实读101479 PENDING(Resources)，101480/101486等待依赖，尚无执行通过结论。
- 25项单位检查、管理结构与diff检查通过。完整3B连续D128、已校准SystemC全系统时间、
  全片/DDR总J/token和FPGA双指标仍未达标；任务继续in_progress，PR235保持草稿。

规则回执：rayggxia-project-collab1.0.0；llm-hardware-design，Issue234/PR235，负责人YUZE-LU。
仅本任务分支/远端目录，无母任务改动；登记PR5 pending，缺board配置/Projects能力，
看板unverified/同步pending，复用Issue7交接；独立审查人待指定，不自审/自合并。


## 2026-11-09 08:08 CST：SystemC内存校验、后端容量与误差归因

- [101479归因结果](cached-integer-result-003.json)：六种小形状、三输入，18次输出与旧适配器逐位一致。
  P0Q1部分KV误差主要已存在于S16权重反量化的FP32结果；P0Q2另有整数配方误差，
  例如next_4_v的整数/反量化FP32相对误差约2.62%而该FP32/HF仅约0.064%。
  两者不能混为DP调度问题；不更改原2%质量门。101492新增前五层逐算子定位，算术不变。
- [101480完整形状重试](cached-integer-full-result-003.json)：debug节点30m06s TIMEOUT。
  P2048Q1在新L1安全证明下三样本通过；P128/P512Q1仍通过。
  P0Q128/P0Q512原整数KV质量失败仍保留；P0Q2048没有完成整数输出，不能称通过。
  38文件、2.727MB包本地/远端与逐文件SHA核对。后续长形状改用c64/c96无限时资源。
- [SystemC/DRAMsim3校验](systemc-dram-result-001.json)：真实SystemC时钟/依赖/队列背压，
  六种配置/输入的回调及全部DRAM计数器与独立直接重放一致。固定上游29817593，
  独立IDD复算发现其total_energy标注pJ但实际单位V*mA*cycles，需要乘tCK_ns。
  保留原版分离队列读→写反例：全部回调返回时仍有4笔写未发出，能量窗不完整；
  unified_queue候选单独标注可排空，不冒充现有控制器。原首次严格检查失败保留。
  无controller/PHY/VPP/终端/板级能量；这只是transport校验，尚非整模型SystemC。
- [完整程序工作量/存储清单](program-inventory-001.json)：六种形状Dot MAC均与独立36层公式一致。
  旧append-only中间结果P0Q512累计409.325GiB；拟议串行最后使用释放的峰值864MiB，
  P0Q2048为6784MiB，均另加权重/谓词/原生分量scratch。该释放模型尚未实现为分配器，
  也未对并行DP调度证明；视图保留整个backing，不把小切片当成完整释放。
  后端存储复用/原生分块改进必须与DP算法收益分列，不用这些结果报token/s。
- DRAM及清单原始包共260个文件的散列已核对，并上传本任务远端local-results-004。
- [资源修订](resource-update-002.json)：只改101486的PENDING配置，排除debug，
  c64/c96、6×10、明确读回TimeLimit=UNLIMITED；先保持101492 held，
  确认101486改为等待101492后才释放。至多一个本任务远程作业运行，链101480→101492→101486。
  101486仍只请求六组自然提示首token，不能把目标D128写成已经执行128token。

当前仍缺：完整3B整数自由生成D128、原生LC/MC/S feeder/互联/时钟与DDR的系统耦合校准、
全系统token/s/总J/token、公开FPGA双指标达标。继续in_progress；PR235草稿，不关闭任务。
规则rayggxia-project-collab1.0.0；登记PR5 pending，看板unverified/同步pending，审查人待指定。

## 2026-11-09 12:12 CST：固定资源的指数包构造与矩阵部署

- [真实E/N/S包构造](n-exp-packet-result-001.json)：规范S32位于S8，现有E op13缩成完整128位[x,0]包写S9，
  N依次Begin/Stats2/Finalize/Exp1后写S10；11原生参考输入×三初态通过全部结果与读回。
  原SRAM写确认/源保持断言及新增三拍完成背压稳定断言都保留。五个命令/输入的整个测试耗时2796667ps，
  **这是测试台时间（含人工背压和读回），不是可直接外推的每Exp服务系数**。
  最终夹具使用整数1ps时基，逐个正沿检查3333/3334ps间隔；早期未声明时基、实数时间截断及错误银行输入路径均留档，
  不把失败的时间结果计入300MHz资格。160文件732356字节包SHA439b1f56c0af9aaea0e45ca9af20fe66fd146aed5d5e8078362c813f0fb1562b，
  所有成员及远端local-results-012完整核验。没有硬件改动；仍缺LC程序生成/实际局控接入、组合物理时序、全模型时间与能量。
- [完整形状数值矩阵](recipe-matrix-attempt-001.json)已提交101543，冻结源5de0ae18与六文件SHA，
  P128/P512 prefill、P512 decode，各RMS1/2且门乘细6位。原相对误差/argmax/全部KV门不变。
  [资源更新006](resource-update-006.json)保留完整命令日志SHA：仅本人PENDING101486的hold/依赖/release，
  链101543→101486，单节点6×10、至多一个本人benchmark运行。12:12矩阵仍PENDING(Resources)，无结果不预报成功。
  101486冻结源不变、仍只请求首token，不冒充D128。数值配方收益不计DP20%。

41项单位测试及管理结构检查通过，原生数据/握手/时钟回放独立记录。固定九组/3M和原外存预算继续优化，扩容以后另评。
任务未完成；完整3B连续D128、整网SystemC token/s/总J/token与公开FPGA双门尚未通过，PR235保持draft、Issue234 in_progress。
规则rayggxia-project-collab1.0.0；登记PR5 pending，看板unverified/同步pending、复用Issue7；审查人待指定。

## 2026-11-09 12:26 CST：共享私有S服务SystemC联动

[U包服务模型回执](u-packet-timing-result-001.json)推进真实S仲裁、注册返回、E/N适配服务FSM和原生流水；
输入没有已测整服务延迟或开始时间。夹具仅从相同命令顺序和背压条件推进，逐事件比较原生RTL。
每个初态341事件（88请求、88返回、55命令、55完成、55消费），三初态共1023事件完全一致，
11个输入的完整数据和S读回仍由真实RTL/独立原生参考检查；整数1ps/300MHz逐沿时钟检查保留。
不允许输入延迟表/额外参数，原程序退出1正确拒绝。-Wall/-Wextra/-Werror编译通过；原生数据断言不放宽。
归档49文件200783字节，SHA ce6e0a39232eaef0cba0ae1e643ed4ef951b744492355cfc3edf3d152fb68cd9，
所有成员和远端local-results-013的SHA核验一致，两个审计源版本、源快照、生成夹具、二进制及日志均保留。

此证据只覆盖串行包服务，未验同时E/N争用、两entry响应队列满载、LC程序/PM/装载、组合STA或整网能量；
测试总时长包含人工保持和读回，不能直接当作每Exp调用时间。物理库和硬件均未变，也没有DP收益主张。
41项单位检查、管理结构及diff检查通过。101543仍等Resources，101486仍等Dependency；队列预报不等于开始/成功。
固定九组/3M/原外存预算继续；完整3B连续D128、校准整网时间/总J/token和公开FPGA双门仍未通过。
继续Issue234 in_progress、PR235 draft，不自审/合并/关闭。登记PR5 pending，看板unverified/同步pending，审查待指定。


## 2026-11-09 09:00 CST：S feeder实际SystemC/活动校准与RMS误差定位

- [S feeder活动](s-feeder-activity-result-001.json)：真实P-S接受网表、原SRAM Liberty与提取RC，六配置（B1/B8、B复用、背压）×三初态。
  全部数据/元数据、持续有效、ACK、独占和最终数组由独立参考核对；36份原始门级VCD功耗分析，
  47623个pin注入、178天线二极管分类沿用同ODB原Lib审计。只在波形比较时忽略经网表证明没有任何单元引用的7位，
  未屏蔽其余连接位；功耗仍用未改原VCD，各初态功率一致。
  B1/B8普通完成可见为28/41拍，复用为12/37拍，背压为33/64拍；另有3拍故意保持done和1拍确认。
  增量约0.207–0.869nJ/任务，包含每32任务摊销的6条quiesce命令，不冒充纯传输系数；持续idle约56.67mW另计。
  背压降低增量不表示降低总能量。前期主机Python SIGSEGV、trace差异和失败日志均保留；重试机制没有证明其根因。
- [真实时钟SystemC feeder](s-feeder-timing-result-001.json)：有限两项A队列、一项B保持、单在途请求，
  并非查表返回整体延迟。32任务×六配置×RTL/最终网表共384组的所有包、完成和确认逐拍一致。
  VCD采样使用时钟前ready/valid，防止下降的post-edge valid漏计；300MHz按有理数边界取整到1ps。
  仍只是S feeder子系统，没有M/局控/母控/互联耦合，不是整模型token/s。
- [101492终态归因](cached-integer-result-004.json)：FAILED 1:0、2m59s，原HF质量门未放宽。
  P0Q2的v782与反量化FP32差约0.00948%，紧接layer3 RMS输出v795差约1.681%。
  共享S16尺度-3使原生最小epsilon实际为0.015625，目标约1e-6；不能把配方问题归为DP。
  全18次仍逐位等于旧adapter，57文件归档及逐文件SHA本地/远端核对。
- [独立非线性诊断](nonlinear-diagnostic-result-001.json)：13组量化输入对FP64参考，7组Softmax、3组SiLU、3组RMS，
  所选分布总体相对L2最高约3e-6。常规分布正确不能排除真实异质行误差。
- [额外RMS迭代候选](rms-refinement-result-001.json)：独立整数平方根核对70次原生N因子，
  相同量化输入和权重，七个异质样本×1/2/3/4/8迭代。2516.5/.2样本从2.59%降至三迭代约5.56e-6，
  但2516.5/.002极端样本八迭代仍约37.5%，因此没有全局开启。默认一迭代指令流与冻结源完全一致。
  这属于增加真实M指令的精度修复候选，不算DP算法收益，不冒充整模型通过。
- [101503捕获](cached-integer-attempt-006.json)等待资源：冻结默认配方，捕获真实layer3 RMS输入/所有中间值及FP32参考；
  后续逐位复现旧输出后再比较候选。[资源修改回执](resource-update-003.json)：只hold/redirect/release本人PENDING任务，
  101503→101486，均单节点6×10，至多一个本任务远程作业运行；101486仍为c64/c96无限时、首token实验。
  [005部署预检失败](cached-integer-attempt-005.json)因Windows换行被bash-n拒绝，未提交作业或改变依赖；006源快照归一LF后通过。
- 四个新局部归档共223MB已上传本任务远端local-results-005，包SHA读回一致；详细原始清单见各JSON。

当前完整3B自由生成D128、SystemC整系统时间/能量、总J/token与公开FPGA双指标仍未达标，继续in_progress和草稿PR235。
精度/配方/分配/硬件变化均与DP20%分列。登记PR5 pending，看板unverified/同步pending，独立审查人待指定。


## 2026-11-09 09:53 CST：母控活动完成，真实RMS归因修正

- [母控采样](mother-activity-result-001.json)：接受的双目标母控、程序SRAM、原Lib和提取RC，单目标/双目标并行/背压三组，RTL/最终网表各三初态全部一致。
  窗口分别688/800/920拍；持续idle约67.715mW，增量约70.36/98.94/78.40pJ每fixture任务，不能替代Qwen指令的通用系数。
  Verilator必须导出underscore内部网络；仅提高trace深度的失败保留。115563个pin获得实际活动，1391个剩余pin在18份分析中各自经ODB和原Lib逐项证明为零自身功耗天线二极管输入，输入负载保留。
  原98.81%覆盖不冒充99%；新增明确的物理分类路径，功能pin覆盖才为100%，未降低原阈值。仍只验收2个resident target，非9目标或整片能耗。
- [101503终态](cached-integer-result-006.json)：FAILED 1:0、2m33s；18份输出仍逐位等于旧adapter，P0Q1/P0Q2未过原HF门，其他四形状通过。
  18份真实layer3 RMS整数输入/中间值/gamma/epsilon和DQ-FP32参考全部回收；81文件包、成员SHA与本地/远端包SHA核验一致。
- [18份真实RMS重放](rms-real-replay-result-001.json)：先逐位复现旧输出，再对相同整数输入比较1/2/3/4/8迭代，105次原生N因子经独立isqrt核对。
  **修正此前归因**：P0Q2 variant0局部误差从0.06896%降至两迭代0.000663%，但相对DQ-FP32整图的1.681%仍为1.680%。
  上游低幅值token行输入已经差1.163%，另一行大outlier使整张输入误差看起来仅0.00948%；不能靠额外RMS迭代宣布整模型修复。
  新observer按最后一维逐行记录误差，下一次默认配方诊断用于定位真正起点。额外迭代保持候选，不全局开启、不计DP收益。
- 新增显式诊断续跑模式，质量失败仍记录false，可继续整数生成；恢复身份包含此策略和源SHA，历史任一步失败永久阻止sequence资格。
  模式不允许源漂移、状态漂移、非整数KV或替换HF现场输入。它只用于收集失败轨迹，不放宽原质量门。
- 两个局部包共91MB、704文件，逐文件/本地/远端SHA核对完成，存放本任务local-results-006。
  36项单位检查及管理结构检查通过。101486仍PENDING(Priority)，原冻结源只请求自然提示首token，远程6×10、c64/c96无限时；不将排队/首token写成D128完成。

仍缺完整3B自由生成D128、整系统SystemC时间和能量、总J/token以及公开FPGA双指标达标。继续in_progress、PR235草稿；不关闭任务。
登记PR5 pending；无board配置/Projects能力，看板unverified、同步pending；独立审查人待指定。


## 2026-11-09 10:42 CST：固定九组、母控SystemC与有限地址分配

- 用户确认先固定九组资源（P3/U2/C1/F1/J2，共3M）及现有外存预算，优化后再评估扩容。
  [约束记录](resource-policy-001.json)绑定旧资源IR的SHA；其中外存仅为两个通道/四银行的编译器抽象，
  不具有已校准器件容量或带宽。任何新外存配置需明确资格，不能用扩大资源制造固定基线收益。
  算法/配方/精度打包/地址分配/硬件收益分别记录；Issue238/PR239仍为独立硬件候选。
- [母控SystemC逐事件校准](mother-timing-result-001.json)：部署后CALL/WAIT/MOVI/END、真实PM银行等待、
  有限信用和返回仲裁，五场景共408次任务/4008条关键事件与RTL及最终网表三初态一致。
  比较包含全部8个CALL参数字；688/800/920/784/704拍，300MHz有理数时间差不超过1ps。
  仍仅两个resident target，未覆盖部署/EVENT/故障/九目标，更不能把fixture服务等待代入Qwen。
  191文件、15.456MB包及前置活动包均保留，实际使用的四份程序镜像已打入包；本地/远端SHA一致。
- [有限外存记录分配](bounded-memory-result-001.json)：实现实际best-fit地址、释放与generation，
  view保留整个backing，完整不可变转置共享同源文件的物理记录；常量/谓词预留，不偷做免费runtime写入。
  六个完整36层形状在64GiB诊断容量下通过，P512高水位50,301,003,600字节，P2048为56,590,387,024字节。
  包含未打包128位标量权重与595008条显式scratch记录；控制程序/完整系统元数据仍额外。
  独立地址与生命周期重叠检查通过；冻结原始Dot/view/Gather等程序抽查516434个地址，均在真实存活backing内。
  四个专项用例覆盖OOM、过期generation、view滞留、转置逐值及晚用常量；全部40项单位检查通过。
  这只是串行有限地址证明，**64GiB不是选择或增加物理外存预算**，也未完成并行DP生命周期/数值RAM整程回放。
  6617文件、17.568MB归档包含六份程序/ONNX、旧地址源与私有ONNX1.17解析器，成员及本地/远端SHA均核对。
- [101514默认配方逐行归因](cached-integer-attempt-007.json)仍排队，随后才执行101486；均单节点6×10，至多一个本任务作业运行。
  新显式rms-refinements参数仅便于之后测试数值配方候选，默认仍1；未把局部修正当作全图修复或DP算法收益。

完整3B D128、整系统SystemC时间/总J/token、公开FPGA双指标仍未达标，继续in_progress及草稿PR235。
规则rayggxia-project-collab1.0.0；登记PR5 pending，缺board配置/Projects能力，看板unverified/同步pending，审查人待指定。


## 2026-11-09 10:57 CST：默认逐行诊断终态与精度候选

- [101514终态](cached-integer-result-007.json)：FAILED 1:0、2m30s；六种小形状共18次输出仍逐位等于旧adapter。
  P0Q1/P0Q2原质量门失败，其他四形状通过；239文件7.084MB已回收，成员及包SHA与远端一致。
- Q2三样本共同发现layer2 FFN门乘v778低幅值行误差0.414–0.626%，down投影v779放大到3.18–4.73%，
  Add后该行误差0.915–1.313%；整体范数仍约0.01%，被outlier行掩盖。RMS随后暴露误差。
  v778指数-10，舍入量级足以解释很大一部分小值损失，**还需候选实验验证因果**。
  Q1后层V误差已存在于S16权重DQ-FP32，是另一问题，不假定该候选能修复。
- 新候选只改变直接送入不可变S16权重Dot的Mul输出格式，允许额外0–6位小数；默认0不变。
  保持S32宽度、相同宏和操作数条数，记录各指数变更；S32动态RHS不进入该策略，S64/分量溢出门仍启用。
  两行outlier专项独立整数对照：旧投影低行raw256，候选raw160与精确参考一致。
  这是数值配方修复，未取得整模型或性能结果，不计DP20%。完整41项单位检查通过。
- tiny实际诊断模式四token连续执行与2+2恢复的KV归档SHA完全相同，tokens仍231/127/225/127；
  tiny通过不代表完整3B。原质量失败祖先资格规则不变，禁止诊断退出0洗白数值。
- 原observer的零参考整体范数会发出NaN诊断警告，旧日志保留；新observer使用float64范数和null相对误差，
  不改执行/质量门。101486仍PENDING(Resources)，未修改其冻结源。

## 2026-11-09 11:29 CST：M Execute SystemC与P_64真实联动

- [M Execute模型](m-execute-timing-result-001.json)：实际SystemC双partial bank、乘积/归约流水、两lane串行缩放及atomic commit，
  不读入已测总延迟。8192个合法resident描述符的load/Execute/read周期与真实原生三初态完全一致，五个非法描述符被拒。
  原生证据完整SHA链已核验；首次编译类型推断错误和修复源保留。仍未覆盖load争用、输出背压、LC/S/DMA或整网。
  48文件232KB包、本地成员与远端local-results-009的包SHA一致。
- [P_64局控联动采样](p-control-activity-result-001.json)：复用已验收的独立M/G/S与父层局控/适配电路，
  原有程序、SRAM最终值和全部断言不变，RTL/最终父层网表各三初态及匹配idle共12次通过；运行窗口363拍、1.21us。
  六份父层活动分析218852个pin获得活动，1427个剩余天线输入逐项经同ODB和原Lib审计，输入负载保留。
  父层idle约43.44–43.46mW，增量每次该程序0.451–0.782nJ，初态差异保留，不取单一通用调用系数。
  M/G/S在父层只用时序抽象，**内部能量没有计入**，不能把这个父层数值当整块P或整模型能耗。
  首次缺失R-only lint文件、其次OpenRAM任意3ns行为延迟造成的功能失败均保留；后者不证明300MHz硬件失败。
  第三版明确复用零延迟活动视图，原Lib/物理验收约束不变。465文件91.697MB包完整成员SHA及远端local-results-010核验完成。
- [数值候选008](cached-integer-attempt-008.json)已排队101535，RMS仍1，只对静态S16权重Dot前的Mul保留额外6位小数；
  同S32宽度/同资源，不计DP收益，尚无完整结果。[资源回执](resource-update-005.json)只修改本人PENDING101486的依赖，
  链101535→101486、单节点6×10，最多一个本任务远程作业运行；101486仍是冻结源的首token实验，非D128。

完整3B连续D128、已校准整网SystemC时间/总J/token和FPGA双指标仍未达标。固定九组/3M与原外存预算先优化，扩容另评。
继续in_progress、PR235草稿，不关闭任务。登记PR5 pending；缺board配置/Projects能力，看板unverified/同步pending，审查人待指定。

## 2026-11-09 11:53 CST：数值候选008终态与N服务SystemC

- [101535终态](cached-integer-result-008.json)：FAILED1:0、2m59s。六形状18次与执行**同一候选程序**的旧adapter逐位一致，非默认程序逐位一致。
  P0Q2三样本由失败转通过，其他四个既有通过形状保持通过；P0Q1仍失败原HF门，未放宽。
  Q2 layer2低值行down误差从3.18–4.73%降到0.081–0.104%，Add后从0.915–1.313%降到0.038–0.043%，
  后续RMS约从1.31–1.76%降到0.066–0.099%。这支持FFN门乘粗格式误差被后续投影放大的归因。
  Q1晚层V的2.06–3.97%误差已几乎全部存在于S16权重DQ-FP32；细化激活不能宣称修复权重误差。
  这是精度配方修正，DP收益仍为零，不是整模型生成或速度结果。60文件5.147MB包逐项、本地/远端SHA均核验。
- [N服务SystemC](n-service-timing-result-001.json)：两lane统计、64步除法/32步平方根及group握手，246个配置与RTL/最终网表三初态共1476次服务一致；
  覆盖RMS/L2长度1..2048、Stats包长1..8及Exp，八个非法/截断描述符拒绝。
  原生因子用独立整数isqrt核对。旧NExp只Stats(x)的错误被7个负输入实测证明；正确Stats([x,0])仍需完整包构造/LC lowering验收。
  源准备路径错误、夹具跨模式Finalize错误比较、首次缺SystemC动态库环境的失败均保留；无硬件或断言放宽。
  107文件24.116MB归档完整成员及远端local-results-011的SHA一致。仍非S/LC/DMA耦合或整网时间/能量。
- 新增明确数值实验脚本recipe_matrix.sbatch：P128/P512 prefill与P512 decode，各RMS1/2且weighted product+6小数位；
  保持checkpoint/权重/质量门和九组资源，六任务×十核、30分钟。下一轮先验证数值修复能否进入完整主场景，不把配方新增指令计作DP收益。
  101486等待Priority，仅首token实验，未更改其冻结源。新矩阵尚未提交作业，不预报完成时间。

41项单位检查、原生/SystemC实际校准与管理结构检查继续分列。任务仍in_progress：完整3B连续D128、整网SystemC token/s和总J/token、公开FPGA双门槛均未达标。
规则rayggxia-project-collab1.0.0；登记PR5 pending，看板unverified/同步pending，审查人待指定。
