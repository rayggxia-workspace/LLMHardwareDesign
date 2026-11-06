# P16 原生服务双块试验

试验复用 [PR #190](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/190) 的 P16 RTL 和 [PR #195](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/195) 的原生服务与确认逻辑。输入清单锁定验收版 P4 SRAM 封装及相关叶宏。P16 源码逐文件对照验收快照，块的两个外部 SRAM 客户分别用于主机检查和链路传输。

试验使用同一时钟域的一个母控、两个局控和两个 P16。母控先 CALL P1，再 CALL P0。P1 局控发出 RESERVE 和 RECEIVE，P0 局控驱动装载、M 计算、G 门控和发送。M 的结果写入 P0.S[8]，G 从各自的输入地址读数，结果写入 P0.S[14]。固定链路读取 P0.S[14]，按预约地址写入 P1.S[20]，目的 SRAM 响应握手才释放源响应。这里单独验证 M 写回和 G 写回，跨块传输使用 G 结果。

局控通过 ENABLE_NATIVE_P16 参数选择试验配置，ABI 0x01790160、拓扑 0x01790161、容量 0x17630001。局控镜像限定为 v2、资源位 0、1 至 8 条执行描述符，object 和 transfer 表为空。L_EXEC 按索引选择描述符，L_WAIT 等待对应 token，程序字保持 64 bit。原生参数留在执行描述符内。母控与两个局控都通过配置端口加载、读回并部署镜像。

在获授权的服务器容器内运行，指定 PR195 验收包的 staged 目录和 issue #155 对应的 SRAM bank 模型。脚本先验证全部输入，再运行正常、双向背压和确认被阻塞时的同域复位重装。

```bash
NATIVE_STAGE=/path/to/verified/staged \
SRAM_BANK=/path/to/s_sram_256x128_freepdk45.v \
VERILATOR=verilator bash project/control_p16_native_v1/run.sh /path/to/results
```

验收限于固定单向、单个 128 bit 在途字和试验复位。跨任务 ACK 身份、生产 M11/M12、CDC、复位认证和组合 300 MHz 时序需要使用生产端点分别验证。[验证索引](../../work/Melodydt/179/p16-native-validation.json)

## A1 候选端口核对

试验基线为 PR #180 `88b633cb` 和 PR #176 `08f2ea20`。核对了 [PR #214 的独立叶宏 P 候选](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/b3e678e9ac445e05638f5496511fb4bede0a6ade/project/rtl/pu_leaf_base/pu_p_group.sv) 与本分支 `block_p16`。两份源码均校验 Git blob 和 SHA-256，53 个同名端口的方向和位宽一致。

| 路径 | 已核对的试验或候选端点 | 需要实现端确认 |
| --- | --- | --- |
| 母控、局控、程序存储 | 两套本地 64 bit 镜像，试验通过配置口装载和读回 | 正式顶层实例、任务／事件和部署互锁 |
| P 内数据 | 两套 P 边界都有 M/G 命令及 32 bit 直连接口。当前 P16 镜像采用 SRAM 回放 | 选用回放或直连，确定实际接点和定点格式 |
| SRAM 和跨块数据 | 每块 16 KiB，10 bit 字地址。外部客户 0 供试验主机，客户 1 接 128 bit 数据链路 | 正式存储变体、读写客户归属、单写者、M11/M12 正向端口 |
| 目的写响应与反向确认 | 试验取目的 `io_rsp_valid[1]`，源端等待后释放 | 正式写响应到反向 ACK 的连接、身份字段、跨域和复位所有权 |

运行 `python -B project/control_p16_native_v1/review_ports.py /path/to/pu_p_group.sv` 可重做核对。加 `--require-production` 返回 2，表示 [清单](a1_endpoint_review.json) 中的 7 项生产绑定仍待确认。历史 A1 校验器绑定旧源快照，在当前提交检测到 `tb_p_compute.sv` 已变化。

## A2–A4 固定试验链回归

`run.sh` 覆盖 13 个服务器仿真场景。沿用实际 P16、母控和局控与同一套镜像，复用已有 ACK 守卫。试验接线从源局控的 SEND 取得 128 bit 服务身份，包含 job、epoch、任务序号和服务序号。目的 P16 的实际 SRAM 写响应才允许接受匹配回执。这是测试台增加的注入与校验接口。

| 验证 | 结果 |
| --- | --- |
| 块内与正常交接 | M/G 的三处读回继续匹配。正常与背压用例中，每次写入只释放一次源数据。连续两任务均逐次检查目的读回和已确认写入。 |
| 回执负例 | 过早、重复、上一任务、四类错身份及复位前旧回执均被拒绝，每项随后由正确回执完成。 |
| 丢回执 | 目的 SRAM 已写入并可独立读回，源端未释放，母控隔离。 |
| 复位重装 | 新 generation 和 epoch 完成装载、读回及执行。上一个 epoch 的回执被拒绝。 |

[验证摘要与结果 SHA-256](../../work/Melodydt/179/p16-ack-trial-validation.json)

## A5 输入核对

[PR #194](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/194) 的九实例试布覆盖 P 内 M→G 和 C/U 传输。[PR #206](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/206) 与 [PR #216](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/216) 提供另一套九宏顶层布线及 2491 网寄生读回。双 P16 组合验收需要同版本的正式顶层网表、上下层寄生、时钟复位约束以及与 A1 端口表一致的实际接点。目标周期为 3.333333333 ns。
