# R 局部状态存储实现（Issue166，验收进行中）

任务：[Issue166](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/166)，[草稿PR167](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/167)。本文描述本分支的新实现，不授予物理资格，不替换 main 或 PR160 的合格交付。

## 实际电路和容量

| 参数 | R256 | R1024 |
| --- | --- | --- |
| 每版本 S32 状态元素 | 256 | 1024 |
| 两版本合计状态字节 | 2048 | 8192 |
| 每版本 256bit 行数 | 32 | 128 |
| 每版本 16行分区数 | 2 | 8 |
| 每分区计算 lane | 8 | 8 |
| 每个 lane 的状态阵列 | 16×32bit DFF | 16×32bit DFF |
| 独立读选择触发器位 | 512 | 2048 |
| 独立写选择触发器位 | 512 | 2048 |

这些容量只计两份算法状态，不含选择寄存器、读/写流水、读回FIFO、key/query、乘积和归约上下文。全部采用 Nangate45 标准单元触发器与逻辑门，没有 SRAM 宏。两版本共同支持同一行读取；每周期最多一个版本、一个行掩码写入。

`r_state_store.sv` 拥有状态数组、局部16位读写选择、每lane写数据寄存器、局部读数据与分区汇合寄存器。`r_stream_local.sv` 拥有指令状态机、原8路整数算术、点积/错误上下文、key/query、卷积历史/taps、读事务标签和四项128bit读回FIFO。

## 边沿合同

存储读请求在 E0 接受，E1 捕获局部选择，E2 捕获局部数据，E3 产生分区汇合数据与有效位。写请求在 E0 接受，E1 捕获局部选择/写数据，E2 写阵列。同一个E2读写同一行，返回写前状态；掩码控制独立32bit lane。

外部读请求使用 `rd_valid/rd_ready`；存储输出在 E4 被控制器放入读回FIFO，`rd_rsp_valid/rd_rsp_ready` 交付128bit。信用计数包括在途与已排队响应，总数不超过4；背压时响应保持。指令优先于同周期读请求，指令和装载等待已接受读事务全部消费；装载还等待写流水排空。计算仍为原流式ISA，延迟有所增加，不是原R的逐拍替换。

reset 清空控制、标签和队列，不清空状态阵列；已排队/在途读取被取消。调用方必须先装载将被读取的状态、参数及历史。结果错误/回滚和跨分块事务沿用原整数参考语料，不用延迟相等作为结果相等的判据。

## 结构与物理约束

仅使用RTL `keep` 属性的初版被Yosys合并，256的读选择产生512扇出，实际审计拒收。当前综合分支显式实例化保留的DFF_X1；仿真分支为同边沿行为。双容量新映射的读写完整组合选择锥均最多32个时序端点、锥内最大扇出32。最终验收仍须验证映射到物理期间保持功能，并测量真实负载/布线。

`local_regions.py` 从真实映射JSON追踪局部寄存器和组合扇入，将跨分区共享逻辑留在外部；生成左右两个版本、垂直分区的OpenDB EXCLUSIVE region及PHYSICAL_CLUSTER group。必须同时建立group成员，否则当前GPL只布局top-level，不能把数据库存在region误当约束生效。最终数据库逐实例检查实际位置。

物理输入从映射JSON重新输出 `-norename` 网表，保持真实实例身份；OpenSTA数据库中的bus括号转义也逐名核对。信号接点放在M10内部，内部布线限制M1–M10。300MHz和I/O SDC沿用冻结合同，未通过不得扩大时钟周期或减轻负载。

## 重跑入口和验收

运行器位于 `project/experiments/r_local_state/`，重型任务必须经Slurm提交；容器与源码先核SHA。组件 `component.py`；整机六独立16核槽动态补位 `engine_v2.py`；按容量读取三个成功回执后 `synthesis.py --capacity CAP --functional-root PATH`。后续依次运行 `physical.py --capacity CAP --mapped PATH --die SIZE`、`evaluate.py --physical PATH --capacity CAP`、`netlist_test.py --capacity CAP --netlist PATH/6_final.v`。`rtl_equivalence.py` 是完整RTL/单元网表顺序等价诊断入口，目前未获得证明，不能声称已通过。`preroute_lec.py` 独立保留Yosys RTL lowering过程，严格验证所有实际状态边界的ABC映射逻辑；最终物理LEC仍单独必验。两者证明范围不能混用。

`resume_placement.py` 复用已冻结GPL/resize结果，真实时钟树生成后才进行hold修复；镜像优化后再次合法化，最终围栏逐单元检查仍必须零越界。`resume_hold.py` 只在真实负裕量的DFF数据端点插入有审计记录的恒等延迟链，所有新增电源连接、最终布局、RC/时序/等价均重新验收；优化顺序不改变原SDC或最终门槛。

单元网表编译两个可执行文件，使用2×16核；完成后`netlist_queue.py`动态补入用例。初始单线程构建以`--case-parallelism 96`使用六组16个独立用例；已启动长用例通过`--reuse-queue --wait-inflight`保留。092实测新增`--threads 16`构建与同源单线程的3项代表结果一致、约1.7–2.1倍加速，因此后续R256最终回归采用6×16槽。队列核验实际Verilator编译命令线程数不得超过每槽CPU；不能将16线程二进制放进96个单核槽。

每个attempt冻结代码、输入、容器、命令和输出SHA。功能组件通过、映射结构通过、布局完成、原生router DRC为0都不能独自授予资格。最终需要提取setup/hold均非负，所有时序/电容/转换时间计数为0，严格LEC和真实故障对照成功，最终原单元网表三初态语料/协议通过，PG/接点/实际局部几何通过，完整未修改原GDS规则检查0，实际LEF/Liberty及六文件绑定全部一致。两容量分别验收。

## 参考与采用范围

- [OpenTitan prim_ram_1p_adv](https://github.com/lowRISC/opentitan/blob/master/hw/ip/prim/rtl/prim_ram_1p_adv.sv)：分块地址选择与读回流水；此处采用分块/流水组织思路，没有引入其具体工艺存储宏。
- [OpenTitan prim_ram_1r1w_adv](https://github.com/lowRISC/opentitan/blob/master/hw/ip/prim/rtl/prim_ram_1r1w_adv.sv)：明确读写端口与时序合同。
- [Yosys memory_map](https://yosyshq.readthedocs.io/projects/yosys/en/0.41/cmd/memory_map.html)：寄存器映射存储的选择/写入逻辑来源。
- [OpenROAD RAM](https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/ram/README.md)：规则阵列布局参考；未引入三态或锁存时钟方案，也不继承其验收资格。
- [OpenDB类型](https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/odb/include/odb/dbTypes.h)和[GPL区域处理](https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/gpl/src/placerBase.cpp)：实际region/group接入依据；以容器预检和日志为最终证据。
