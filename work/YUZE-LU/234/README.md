# Issue234：Qwen3B SystemC 时间、能量与充分优化对照

2026-11-09 CST，YUZE-LU，[Issue234](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/234)。
独立分支 task/234-systemc-benchmark，正式提交以已知main c4d7b960为底；老算法从375b8fca0/在线冻结1d284bdc只读核对。
不修改母聊天的算法工作树、活动分支或作业。

任务未完成。不得将已有B1/S2无KV模型代价换算、单宏资格或下面的合成测试宣称为整网SystemC/焦耳验收。
用户要求持续多轮直至达到经核对的FPGA门槛；初始主场景拟Qwen2.5-3B B1、输入512、decode128，补128/2048上下文。
主门槛已异步询问，未收到选择时不把暂定口径说成用户确认；对照用平台原生充分优化配置，不强制退到我方标量布局/数值格式。

## 交付顺序与硬门

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
