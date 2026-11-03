# DRAM读事务经FIFO直供M（Issue173）

本实验实现控制器用户接口之后的数字通路，不经过S：

```text
300MHz描述符/请求生成
  → 请求异步FIFO（49bit）
  → 500MHz侧单在途16B读事务接口
  → 返回异步FIFO（138bit，含数据/错误/装载位置）
  → 300MHz装载器：A128保持，B按四个128bit字拼成512bit
  → 原版block_v2_m：A/B本地银行、归约/累加/结果
```

本仓库main没有完整DDR控制器/PHY；PR159有外存事务/AXI仿真合同，不把其有限DMA当作DDR控制器。本实验使用独立只读内存事务模型，实际计算由不变的main M RTL执行。平台实际AXI/DDR接入仍需外部控制器、协议桥和完整通道CDC；本模块不是完整AXI桥。

## 固定合同

- M固定为main `4b1df2c7cbdaa0fa6f9f468f2b5b854cec875609` 的 `project/rtl/block_v2/block_v2_m.sv`；不改M源码。
- `dram_m_fifo_loader`输入一次LOAD描述符：40bit A/B字节基址、bank、rows1..8、tiles1..4、双侧S8/S16格式；基址16B对齐。保守拒绝40bit末端加法溢出。
- 外存口是valid/ready的单在途、顺序128bit读接口。每个请求读16B，响应至少晚一个mem_clk。请求、返回在背压时保持，错误随返回交接。数据来自模型，不代表真实DRAM时延或刷新。
- 软件预打包A为每行每K8一个16B槽（S8用低8B），B为每tile列优先8×8的64/128B；B先装，再装A。不能将任意矩阵行主序直接接入。
- 请求和响应均使用独立时钟FIFO，深度参数为2的幂且>=2。Gray指针和两级指针同步，空/满由本域判断；payload不复位。
- 外存侧发读前至少有一个返回槽，最多一个外存读在途；发出后只有该事务可占该槽，因此即便下游停止，也保留其返回容量。两FIFO、B拼接寄存器、A/B保持项分别计容量。
- LOAD完成要等所有请求返回、所有已发布A/B包被实际M接收。完成信号背压保持；新LOAD在当前完成被消费前不能进入。
- 一旦读错误，继续排空该描述符全部读事务，但不发布后续A/B包，报告失败；已经写入的M银行不回滚。调用方必须使该目标银行失效，禁止失败LOAD后计算。
- 首版不自动触发GEMM、不自动STORE结果，也不实现B跨LOAD复用、多个LOAD并发或任意控制命令并发。主机只提供描述符和M命令，不能直接注入M操作数；测试从M原生响应口核对结果。
- reset必须与平台在途事务协调：异步置位、两域各自同步释放，清空队列/控制；不支持只复位一域后继续接收旧响应。仿真复位同时放弃内存模型在途事务。
- 同一个300MHz时钟时可选择同步实现减少CDC延迟；本实验保留双时钟结构作为对照，不宣称其延迟最优。

## 服务器复现

在独立Slurm分配、源副本及全新输出目录中运行：

```sh
python3 -B project/experiments/dram_m_fifo/run.py --verilator /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator --jobs 8 --out /absolute/new/output
```

两种FIFO深度2/16；mem/core时钟为500/300、300/300、200/300MHz，不同相位和零/一/随机初态，共18个独立运行。相同频率案例不默认同相，仍验证异步结构。每例包括128组随机/尾K/尾N/双银行/S8与S16矩阵、错误排空与重载、在途复位与恢复；独立整数oracle逐值检查M的S64结果。还检查实际请求地址/顺序、A/B数据和元数据、背压稳定、无提前完成、非法描述符无内存访问、满边界及指针多次回卷。每种深度另以真实内存返回数据翻转一位，要求检查器拒绝。

`dram_m_fifo_tb`是测试连接顶层：真实loader与真实M之间插入可控停顿，valid/ready成对门控，不替代M计算。内存模型响应延迟1..9个mem_clk，单在途；这些设置用于功能与流控覆盖，不是某个DRAM器件的性能模型。测试watchdog只捕获逻辑不前进，不用作EDA耗时取消依据。

输出保存源码/工具/构建/运行/负控制日志、参数、终态和SHA。仿真不证明模拟亚稳态可靠性、同步器物理约束、双时钟存储宏可实现性、500MHz时序、面积功耗、DDR板测或整机物理资格。实际结果在本任务报告中单独记录，不把本合同当作已通过回执。

## 500MHz → 300MHz 物理实现补充

`dram_m_direct`是物理顶层：移除测试停顿开关与操作数观察端口，固定两个FIFO深度16；接入同一份loader与不变的M。M复位也同步释放。请求方向为300→500MHz，数据返回方向为500→300MHz，两个方向都进入物理实现。

使用固定ORFS容器、Nangate45 typical标准单元，把FIFO、适配器及完整M一起平坦综合、布局、双时钟CTS、详细布线和寄生提取。没有套用已有M的物理数据库，也没有用行为RAM替换FIFO或M存储；内存控制器/DDR PHY属于顶层外部。

```sh
# 在各自全新Slurm任务目录内；下列每个OUT都必须不存在。
python3 -B project/experiments/dram_m_fifo/physical.py --mode map --jobs 16 --out NEW_MAP/output
python3 -B project/experiments/dram_m_fifo/physical.py --mode pnr --jobs 16 --reuse NEW_MAP --out NEW_PNR/output
python3 -B project/experiments/dram_m_fifo/physical.py --mode audit --jobs 16 --reuse NEW_PNR --out NEW_STA/output
python3 -B project/experiments/dram_m_fifo/physical.py --mode gate --jobs 8 --reuse NEW_PNR --out NEW_GATE/output
```

源副本根需提供`source-snapshot.json`记录提交SHA；runner验证复用输入的RTL、库、网表哈希。`gate`不提供`--reuse`时检查生产RTL，复用map时检查综合单元网表，复用pnr时检查实际最终布线单元网表。生产口测试有131个矩阵/次，包含实际M银行锁造成的阻塞；不依赖测试专用停顿开关。

时序合同：mem周期2ns，core周期10/3ns；不确定度0.1ns；时钟转换0.05ns。外部接口预算mem max/min为0.4/0.1ns，core为0.8/0.2ns；BUF_X2输入驱动、输出50fF。`set_max_delay -ignore_clock_latency 2.0`约束所有跨域路径，min为0；每一对同步器stage1→stage2另约束max 0.30ns。实际检查两级同步器与每位Gray连线，不设置整组异步时钟false path。原始reset只对复位同步器实际异步引脚作精确例外。

独立STA在新OpenROAD进程读取最终ODB、实际SPEF和原始精度SDC，检查两个传播时钟、setup/hold、40条同步器路径、电气限制、端点覆盖、寄生覆盖与信号输入连通性。这里的跨域延迟上界是约束与布线检查，不是模拟亚稳态MTBF或真实芯片PVT签核。最终结果另见物理报告；流程运行结束本身不等于通过。
