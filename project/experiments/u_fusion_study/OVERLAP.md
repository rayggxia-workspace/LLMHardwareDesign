# Issue247：隔离的 N/E 生产消费重叠候选

这是新实验准备，未修改生产 RTL，也未修改已冻结的 `prepare_native.py`、`run_native.py`、`parser_selftest.py`。它不能作为生产实现、实际 token/s、S32 数值合同、面积或 300MHz 的证据。实际 RTL 编译/运行由 root 独立源锁和 Slurm 作业提供。

`overlap_control.sv` 是可综合的有限寄存器 FIFO 与调度控制，不是预知耗时的模拟器调度。整个 bench 只实例化一个生产 `pu_u_group`，因此只有一个 N、一个 E、一套原 S/仲裁器。原 N/E/S、算术舍入、服务状态机和内存时延保持原样。

## 实验合同

- N 只发 RMS replay（8 个 S16），N 结果经 valid/ready 被 FIFO 接管后，才确认 `n_done`；此后才能发下一 N。每个 FIFO 项含 128 位数据和 8 位 tile 标签。
- E 独立发 ADD。发起时占有队首标签，命令在背压下保持；A 被 E 接管时 FIFO 出队，但 E 槽仍占用，直到原 `pu_compact_e_service` 最后 S 写响应之后的 `e_done` 确认。
- E 的 B 从原 S 读取，最后结果写原 S。N 两个输入也从原 S 读取。双方仍竞争现有单事务 S 仲裁器，没有新增 SRAM 端口，没有免费重叠 S 事务。
- FIFO 的输入 ready 仅依赖寄存计数和 reset；没有 E ready 到 N ready 的组合路径。满 FIFO 同拍 pop 不接收新 push，复苏的一个气泡如实计入周期。输出由寄存数组和读指针选择，在 stalled valid 期间保持。
- 深度 1/2/4 分别编译独立顶层，每次只有一个 FIFO；每个深度依次运行 rand 模式 1:143、2:143、2:144，不并行编译超核。
- 输入全部相同，RMS 统计准备放在计时外；每个 tile 输出 N=1024，B 槽 `128+t` 的八个 S16 均为 `25+t`，最终结果槽 `64+t` 期望八个 S16 均为 `1049+t`。每次检查所有目的槽，防止常数数据掩盖丢失或错序。
- 比较原 `pu_u_direct_pair` 的 0x104 串行控制与新 FIFO 控制。两路线都为 1/16/32 tile、handoff delay 0/4，每 tile 必须真实 S 读 3 次、写 1 次；命令与 E A 接管各一次。延迟只在下游实际可接管时付费。
- 单次流从发起到最后 completion 确认计时，setup、最终 S readback 不计入。串行基线按原合同每对 ACK，新流最后排空 ACK；新控制实际节省或增加的控制拍均计入。
- 另做 consumer pause：等 FIFO 真满且 N 真正 held，再保持 8 拍，随后恢复；另在同状态全组 reset，检查 FIFO/valid 清空，再初始化并核验新 tile。守恒、标签顺序、N/A 背压稳定、最大在途数和全部结果由 SV 检查。

最大在途数定义为 N 已接受命令数减 E 已确认退休数，包含正在生产的 N、FIFO 内项和 E 当前项，硬界为 `DEPTH+2`。FIFO 的新增数据/标签寄存位为 `136*DEPTH`（深度2为272位/34B），另有指针、计数及调度状态；不是 SRAM 扩容，也不等同于综合后的精确 FF 或面积。现有 N 输出和 E 内部寄存器不算新增 FIFO 存储。

## 运行

依赖清单在 `overlap-dependencies.json`。原 U smoke 的 common+slot3 自动解析并校验 SHA；包含的 `block_v2_n_exp.svh` 单独记录 SHA。外部 SRAM 宏固定 SHA；工具可执行文件也记录 SHA 和版本。runner 先严格 lint 新控制器，再按原 smoke 的 warning 策略构建整个未修改生产依赖。

在 root 的独立 Slurm/container 包内执行（路径由 root 冻结）：

```bash
python3 source/project/experiments/u_fusion_study/run_overlap.py \
  --repo source --out results/overlap --workers 4 --manifest inputs.json
```

`--manifest` 必须提供真实 40 位 `source_commit`；输出目录必须不存在。每个深度逐个编译 `-j<=4`，整个 runner 要求实际 `SLURM_CPUS_PER_TASK` 配额。结果持久化于 `results/overlap/result.json`，含源码/脚本/宏/工具 SHA、实际命令、退出码、日志 SHA、108 个普通测量（3深度×3随机配置×12项）以及满/空/复位回执。

本地已执行：Python AST 解析、原 TB SHA/锚点检查、文本生成；日志解析器 3 个合成正例、30 个定向负例。它们只是生成和解析检查，**RTL lint、编译、仿真均未执行**。服务器结果必须成功后再作性能判断。

## 边界与后续

控制器仅承诺本 workload 的成功路径；异常将置 sticky fault 并停止新发起，必须重置整个 U+FIFO+控制器恢复。没有声称完整的错误 drain/cancel 协议或局部复位安全。现有 native 实验单独覆盖原串行 pair 的错误取消。FIFO 流的错误恢复、任意算子/维度、运行时重新配置、跨 block 路由、跨时钟、S 地址别名、生产顶层命令 ABI 和时序收敛均未验收。

先根据真实结果判断 N/E 是否存在足够可隐藏的服务尾部；即使 FIFO 很小，S 仲裁和 N/E 各自单命令入口仍限定可隐藏部分。若样本提速不足，不能仅用 `max(N,E)` 替代实际周期。后续最小生产化范围为固定两项 FIFO、标签/目的归属、错误取消与 drain、顶层命令 ABI 和同一实际宏下的综合/STA；无需复制 N/E 或扩大 SRAM。
