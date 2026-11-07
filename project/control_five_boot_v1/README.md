# 五类 Block 的统一 PM 与装载控制

Issue179 / PR180；综合前第4步。`five_boot_top` 是编译期选择 U/F/C/P/J 的两目标候选：一个现有 MC、两个现有 LC（ID0/1）、三个真实可综合 PM。每个变体的两个目标同类；五类同时驻留、异构跨块连接属于后续步骤。

## 硬件路径

主机命令 → `typed_boot_front` → **原有且未修改的** `control_boot_manager` → MC/LC 配置接口、三个 `control_pm` → 64 bit 取指执行 → `native_control_endpoint` → 原生组实际端口。`five_control_top` 负责公共复位、任务/返回路由与 host/start 互锁。原 `control_boot_top` 和双P数据链路保留。

功能回归使用冻结 PR213/214 的真实数据通路、S wrapper 和 OpenRAM bank 模型；PM 可选推断同步 RAM 或四 bank 后端。结构检查单独把数据组和 bank 明示为黑盒，仅验收控制与连接结构。目标周期仍为3.333333333 ns，本步骤未进行新增组合映射、STA、CTS或物理验收。功能模型的仿真周期不构成时序证据。

| KIND | 原生类型 / 数据组 | 当前控制路径 |
| --- | --- | --- |
| 0 | U / pu_u_group | E、N；S存取与回放；直接N→E边禁用 |
| 1 | F / block_cfj_cf KIND=1 | E、G；实际RX提交写S与TX读回；late边禁用 |
| 2 | C / block_cfj_cf KIND=2 | E、G、R256；同一真实S路径；late边禁用 |
| 3 | P / pu_p_group | M装载/计算、G；经S回放；直接M→G边禁用 |
| 4 | J / block_cfj_j | 带tag/slot/last的真实片段输入、T提交输出、显式释放；late边禁用 |

此处KIND是**原生能力命名空间**，与理论ISA中的类型编号分别解释。ABI=0x01930001，topology=0x01930011+KIND；实际64 bit v2指令不变。U/F/C仅开放原生COMMAND(0x100)，且native3=0；P开放LOAD/MAT/GATE(0x110..0x112)；J开放JOIN/RELEASE(0x120..0x121)。不支持的服务在endpoint返回4，不驱动数据组。保留实际服务身份、饱和标志和确认读写字节数。

LC的候选image_id在BEGIN成功回复后才提交；失败BEGIN不能改写MC引用的现有image_id。原有MC/LC及PM/装载管理器源码在本步骤不变。

## 管理命令和J适配

公共命令0..12及字段逐项沿用[装载接口](../control_boot_v1/README.md)。命令是独立4 bit主机端口，不是新增执行指令。请求/响应均ready/valid，最多一笔在途；响应保持到主机接收。普通S的128 bit数据按16 B字节地址访问。

J对11/12(S_READ/S_WRITE)返回4。仅J开放以下两项：

| cmd | 字段 | 完成依据 |
| --- | --- | --- |
| 13 READ_NATIVE_OUTPUT | target=1/2，address=0，data=0 | 返回真实T输出捕获包；主机接收回复时才pop；空返回0x105 |
| 14 WRITE_J_FRAGMENT | target=1/2，16 B对齐address；data[127:0]片段，[159:128]tag，[161:160]slot，[162]last，余位0 | 驱动实际J输入端口，等待真实提交回复；rx_error返回5 |

13返回512 bit：payload[127:0]、tag[159:128]、index[169:160]、last[170]、实际CALL的job[202:171]、epoch[234:203]、task_sequence[266:235]，高位0。每个J使用4项FIFO，捕获真实输出握手；RELEASE释放的是原生T，而FIFO所有权一直保持到主机接收。每任务最多一次JOIN、1..4字，超过边界拒绝，避免依赖主机在运行中读取而死锁。

J原生epoch为8 bit，RELEASE只接受1..255并在真实释放握手捕获；示例tag高8 bit与epoch一致。32 bit主机epoch字段不意味着J具备32 bit原生世代。运行、未消费RESULT及未消费原生输出期间拒绝相关写入/新START(0x106)。先消费RESULT，再逐包读取J输出，排空后才能开始下一任务。`link_pending_o`在本候选专指未消费原生结果，并非已连接跨块链路；跨块commit/ack计数固定0。

## 回归与独立参考

`images.py`使用当前v2/64 bit汇编器生成三个真实镜像、CRC32和独立数值参考。U包含RMS分段统计、归一化、统计读回、带S0毒值的两源FMA；F/C包含门控及E加法，C另含R状态装载读回；P含M装载/点积和G写回；J含两分支四字T输出、完整任务身份和消费互锁。U RMS epsilon=1符合原生约束，整数平方根使本组±1024参考保持精确。

7个模式：正常、连续两任务/新数据、装载CRC中复位、真实PM读回破坏后拒绝和恢复、错误generation/ABI/image_id拒绝、ABORT后重装、未支持服务错误退役后复位恢复。每模式使用两种PM后端和三种初态/随机种子组合，即每类42场景，共210；响应背压和运行写入互锁贯穿测试。场景通过率不等同功能覆盖率。

服务器上准备[冻结输入](../control_frontend_v1/README.md)，使`NATIVE_STAGE`下含native-p/design、cfj/design及其staged依赖；bank SHA必须匹配脚本中的锁。使用Slurm在获分配计算节点运行：

```bash
KIND=0 NATIVE_STAGE=/path/to/frozen-stage SRAM_BANK=/path/to/bank.v VERILATOR=/path/to/verilator BUILD_JOBS=4 bash project/control_five_boot_v1/run.sh /path/to/results/U
python3 -B project/control_five_boot_v1/check.py --kind 0 --stage /path/to/frozen-stage --bank /path/to/bank.v --verilator /path/to/verilator --yosys /path/to/yosys --out /path/to/structure/U
```

KIND依次0..4。`SMOKE=1`只执行OpenRAM后端正常模式，不替代全矩阵。原生组为只读依赖，本模块不修改Block数据通路。最终结果、源码与输入/输出SHA-256见[技术验证索引](../../work/Melodydt/179/control-five-boot-validation.json)。
