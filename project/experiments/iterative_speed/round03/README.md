# R3：真实有限 M 服务的旧 SystemC 评价接入

Issue 247 / PR 243。此目录是独立生成器；R1、R2 和旧容量/端口生成器均不修改。R3 关闭时删除唯一新增 `iteration3_study` 字段，完整 RESULT 必须等于 run19 对应 R2 已启用回执。当前实现尚未经过本地 C++、RTL 或 SystemC 执行；正式编译和执行由统一 Slurm 作业完成。

## 接口与来源

正式位置为 `project/experiments/iterative_speed/round03`。运行：

```sh
python3 -B project/experiments/iterative_speed/round03/run.py --root /path/to/run
```

根目录须提供 `source/`、`inputs/` 中冻结的旧 trace 与 m-profile.log、`inputs.json` 中源码和输入 SHA、`run19-result.json`、`r1-calibration-result.json`（run16）、`r2-calibration-result.json`（run18）、`calibration-result.json`（本轮实际 RTL）。三份旧回执的 SHA 在 runner 中固定。新 RTL 回执的 SHA 由本轮输入清单绑定，生成结果还保存该 SHA、代码 commit、真实 SRAM/控制器 SHA、控制重放源码 SHA、六次实测日志及控制 SHA。

模型命令在旧完整参数之后追加 `R3_BUFFERS`，只能是 0、1、2；R1/R2 都须为 1。开启 R3 时没有通过所有数值、有限资源、生命周期、真实 SRAM、默认对照和控制重放门的校准回执便拒绝。ACK 延迟必须来自全部无人工延迟的实际资格用例，读和写各自只能有一个接受到消费间隔；不能取最小值或猜测典型值。`control_probe.cpp` 与 `finite_control.hpp` 先由独立原生校准作业对真实 RTL 每周期逐字段验证。

## 替换范围

仅 static layout0、rows1、A32、运行时 W8、shift16、N 整 8、fullK 为 2048/11008、old tile K256 的路径使用新服务。W16、动态 attention、prefill rows2 和未覆盖的尾块完整回退。资格按格式/形状判定，不依赖 workload 名字。

保留旧 producer 的实际 DDR 请求、64B beat、17.1GB/s、300MHz 时间单位、2P、16KiB/P、前缀/驻留判断、adaptive policy、A 两 bank 引用和 B 两 token、列分配、8 context 顺序、旧输出 WB、DMA 与 flush。改变的窗口从旧 tile 的输入 DDR ACK 全部完成之后开始：移除该 tile 原输入 S 聚合预约、adapt、compute、tail/max，改为 16 条 K16 原生描述符的有限控制器；完成输出的旧 `p_result_store` 也移除，因为候选内部已经做了两次真实 16B 写预约和 ACK。

每个 old tile 的所有 tickets 退休后才进入下一 tile；保留每 P 的 S96 context 状态，但不跨 old K256 边界预取。服务入口向上对齐到绝对核心时钟边沿；最后 completion 接受后推进一拍才返回，避免相邻 tile 在同一边沿双重接受。原 context 选择 1 拍仍在外层收取。旧 `context_study` 的 “per M command” 描述沿冻结字段保留，其在新路径上的单位应读为 **每 old tile 选择**；真正新描述符数在 `iteration3_study` 独立列出。

## 有限资源与 S 预约

控制镜像含 BUF1/2，每槽 256B（A64+B gather192）、2 条读响应 metadata、8 项有序 completion、reserved/committed K 前沿、同一 context 提前读、单 writer、final 两写 ACK 与 context 释放。叶 M 的输入释放、流水推进、提交和输出反压采用校准后的同一控制模型。性能模型不执行张量算术；数值资格来自独立原生 RTL 大整数比对，不能称整图数值证明。

每拍仅当对应 Calendar 的 `[edge, edge+1cycle)` 可用才给 ready 并预约；未接受、被写优先撤回的读不占预约。已接受的请求按实测延迟进入有限响应队列，等待 S 时 core 和已有 ACK 仍按状态推进。每包 A64+B128 各自真实读取，不继承不存在的 A RF 缓存。旧 ctx8 A 复用仍只是在外层减少 DDR 加载，wrapper 没有验证完整 DMA 租约。

候选检查 Calendar 前和原 reserve 一样删除已过期区间，区间表不会按累计请求数增长；metadata 记录同时存在的区间峰值。producer 对每个资格 tile 都先检查完整布局，而不是等 descriptor 失败再减少覆盖：驻留 A 或 prefix、两 A bank、两 B bank、旧部分和预留均须位于顶部工作区之前。主配置输出占原 1024B 工作区的首 256B（地址 14848–15103），原 512B WB 单独保留在 15872–16383；候选仍保留中间未用工作区。全部不超过 16KiB，输入和输出地址不得重叠。

输入一块 K256 仍是 3072B/48 拍 S 服务，但预约数由原 1 次聚合变为 48 次。末输出从原 1 次抽象 64B 服务变为 2 次 16B 服务，所以每输出增加 1 拍和 1 次预约。这些差额从 trace 独立推导，不能虚报完全相同 S 费用。新寄存器槽不扩容 SRAM。

shared 层逐次竞争旧统一 Calendar；idealdual 层沿旧理想分离读/写 Calendar。wrapper 自身每拍读写仍互斥。真实四个 1RW 宏的总操作上限是 64B/拍，不能将 idealdual 层叫成现硬件测量。旧 DMA 的 S 写回仍是原 Calendar 抽象，尚未与原生 wrapper 共享真实 SRAM response FIFO，因此本轮也不是完整 P/DMA/DDR 联合 RTL 时序校准。

## 计数与性能解释

`M_tiles` 保留 old tile 数；资格路径 `M_commands` 改计真实 K16 描述符。`M_work_ticks` 对新路径计有效 core 推进边沿，`adapter_work_ticks` 计接受的 64B 输入读取；二者的新旧含义不同，不能据此直接算加速百分比，也不能把累计占用加成端到端时间。metadata 单列移除的旧费、实际 issue/commit/completion、读写请求/ACK、控制周期、S 日历等待、入口对齐与有限峰值。

真正时间由状态机与 Calendar 共同产生，禁止用单包 wall 乘 16、与旧 send 再取 max、或把 leaf II1 套到整个 P。若 BUF1/2 性能退化，报告保留负结果，最佳配置允许是 R2 基线。

## 执行与检查

24 个主 case：四个冻结场景（W8 decode512、W16 decode512、W8 decode2048、W8 prefill2）× shared/idealdual × R3 off/BUF1/BUF2。先完成 8 个 off 全 RESULT 回归，再执行候选。五个小 trace 各运行两个端口层的 baseline/BUF1/BUF2：resident K2048、8context/prefix K11008、K/N 尾块、A16 回退、W16 回退。

审计核验实际校准命令/日志/控制重放绑定、buffer/seed/fullK 覆盖、DDR logical/bus/descriptor 和 U 工作守恒、有限读写与 completion 守恒、每 P S 服务/预约差额、形状命令差额、旧字段完整回归。关键篡改负例涵盖来源、未通过门、ACK 伪费、额外 buffer、缺 ACK、免费写 S、隐藏 command、DDR/U 改动和虚假物理资格。旧 kernel/validate/smoke 也使用实际生成 binary 执行；它们不替代新有限控制校准。

所有正式结果由服务器 `results/result.json` 记录，失败时也保留已执行阶段、错误和 traceback。源码、生成源、输入、工具、日志及实际回执均留 SHA。当前本地实际执行仅为 AST、纯 Python 生成与冻结源 SHA 对比；RTL/C++/SystemC 测试未在本地执行。

接入前已核对实际 run20 校准（源码 `a3149d69a23f52efb808dbbb46b5558dffce4df7`，结果 SHA `87842b59e42fb0773eedb82dce4981614432868fa12218c3aa15166b0b839eff`）：六次真实 RTL 运行每次 66 case、7638 checks、20 reset case；七项门通过，读/写接受到 ACK 消费均为 2 拍。独立核验了回收的 411 份命令日志/事件文件 SHA。此项通过仅授予相同控制源码和受限形状的本地服务校准，不意味着本目录整图 SystemC 已运行。
