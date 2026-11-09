# U连续算子融合与有限缓冲重叠

Issue247 / PR243，负责人Melodydt。冻结前轮分支2f875d2f5cdd76c6eb17187bf6d836de1248b466及run05真实结果，研究连续算子中间量旁路、单E执行资源下的供数/执行/写回重叠，并独立测量现有原生N→E通路。只新增隔离研究，生产RTL与SRAM容量不变。

两层证据分开：条件架构模型沿用PR241原生S32/96位M与流水E32假设；原生RTL使用已有S16宏、真实SRAM功能模型和现有直连合同。不得将二者性能或物理资格相互转移。旧模型已有canonical寄存器复用和P DMA重叠，本研究不重复计算这些收益。

只有依赖、布局/范围、生命周期和资源容量均满足的中间量才允许旁路；保留数值舍入顺序。归约后的全行依赖、多消费者和超容量情况必须回退。有限FIFO不等于增加E/N计算实例；控制代价敏感性须同基线公平计入。

`generate_fusion.py`复用已冻结的run05生成链，只替换elementwise向量region；NExp、canonical、归约与P实现保持。相邻、唯一输入使用、同S32范围的E→E边可用256B数据＋32B元数据寄存器转发。每算子的原算术/舍入边界保持；新增转发控制成本单独比较0/1/3周期，不减掉旧模型没有收费的发令开销。

`fusion_contract.py`与`u_ledger.py`独立重推合法边、U有限缓存、真实访问/DDR与S服务。`fusion_audit.py`将这些结果与实际C++完整trace及逐packet事件匹配；默认必须剥除新增观测字段后逐字段回归run05。

`replay.py`是单E、单输入/输出控制器、深度1/2/4/8有限槽的条件事件重放。每槽768B输入＋256B输出，另有256B转发寄存器；控制面积未实现/未测。维持数据依赖、单E原序、写ACK、转发带宽和生命周期及region屏障。DDR/缓存阶段时长冻结，结果必须标作条件预测，不能冒充并发SystemC或RTL端到端实测。深度1必须逐region复现串行结果。

`prepare_native.py`/`run_native.py`测量已有生产S16 N→E通路，比较相同RMS回放→ADD的经S与direct路径：1/16 tile、0/4拍交接等待、三初态及错误取消/禁用/复位。RMS统计准备与结果核对在计时之外，现有配对控制仍一次一项；不把局部提速称为整图token/s。使用真实冻结SRAM功能模型，原13份U RTL及测试接线均经SHA锁定。

在本人Slurm目录运行：

```sh
python3 -B source/project/experiments/u_fusion_study/run.py --inputs inputs --out results --prior run05-result.json
```

以`job.sh`申请4核c64/c96、UNLIMITED，在固定ORFS容器和SystemC3.0.2/Verilator5.042环境执行。原225 kernels、4 validation、5 smoke及独立oracle保留；计划22完整trace，先9个默认回归，再13个实际融合/控制代价对照。输入SHA、前置完整回执/manifest与source.json全部绑定，P源码生成文件必须与run05逐字节一致。实际运行结果以完成后的回执为准，管理结构检查不替代业务或物理验收。
