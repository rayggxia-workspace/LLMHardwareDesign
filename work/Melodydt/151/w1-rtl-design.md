# W1 固定 DOT8 可变输入 RTL 草稿

研究 parent 为 `bfe62ad179af72aef591622aa5c7a000f5d8b681`，native 固定 `707878621b2add4ed218b8c43df2e95c9a56e2ba`。本目录新增 `block_w1_mst_top.sv` 与 `block_w1_mother_rom.sv`；原 P2、S helper 及 M/S/T 叶文件不修改。此稿等待独立 RTL 仿真，不能视作完整大 Block、模型或物理验收。

公共输入为 `clk/reset/abort`、`in_valid/in_data[127:0]`、`start_valid`、`done_ready`、`out_ready`；输出为 `in_ready`、`input_stored`、`start_ready`、`busy`、`done_valid/done_error`、`out_valid/out_data[127:0]/out_index[9:0]/out_last`。reset 为同步高有效，abort 是协调取消语义。

## 入口与帧绑定

每帧顺序接受 8 个 128-bit beat，一次仅一个入口事务在途。`input_index` 是隐式索引，外部没有地址、shape、op 或 scale 配置能力。

| beat | 实际 S 地址 | 写入规则 |
| --- | --- | --- |
| 0 | 448 | 输入低 64 bit 的 8 个 S8 A；高 64 bit 硬件写零 |
| 1..3 | 449..451 | 无论输入值为何，实际写 128 bit 零 |
| 4..7 | 452..455 | 原样 128 bit，按 n-major 排列的 8 个 B 列，每列 8 个 S8 |

入口先锁存 canonicalized 数据，`INPUT_REQ` 向唯一 `block_p2_s_ctrl` 提交写请求，`INPUT_RSP` 等待 helper 消费 native 普通写 ACK 并返回响应。只有该响应再次被 top 消费才 advance `input_index`。因此 `input_stored` 至少晚于第 8 次输入接受和第 8 次真实 S 写 ACK；不是仅对外部握手数计数。A 的全部 56 字节 padding 真正被写零，不依靠 reset 清 RAM。

`frame_active` 从首 beat 接受保持到 done 被消费。`frame_stored` 从第 8 个 helper 响应保持，正常 RUN/DONE 期间仍绑定当前帧；`launched` 在一次 start 接受后禁止再次 start。只有 `frame_stored && !launched && mother_start_ready` 才能接受 start；早到的单拍 start 不排队，持续 valid 可以等到 ready。RUN 或 pending DONE 不接受任何新帧。

`busy = !reset && (frame_active || mother_busy)`，覆盖部分输入、已存储未启动、RUN 和 pending DONE。done 被消费后清理三个帧标记及索引；下一帧必须重新完成全部 8 次写入和 ACK。

## 固定程序与 S 唯一 owner

ROM 继续使用固定 21 条 SERVICE/WAIT/END 指令。service slot2 的 `S_INIT` 改为 `INPUT_CHECK`，只验证 `frame_stored && launched`，不产生任何 S 写。其它顺序保留：M CLEAR → factor1/left_shift0 → INPUT_CHECK → loader → EXEC → 四个 M op3 结果写 S → T BEGIN4 → S 读并写 T → COMMIT → 对外 READ → RELEASE → 成功 done。

几何固定 A/B=S8、rows=1、tiles=1、K=8、N=8、bank0，EXEC op10/index0/data=`0x9884`。M 配置和 EXEC 响应只作为 ACK/status；检查 error 和 EXEC fault_rows 后才继续。只有四次 op3 的 2×S64 响应被作为结果写到 S456..459；每次写 ACK 被消费。T_FILL 四次 S 读应答依次写入 T，T 四字真实消费并显式 RELEASE 完成之后，ROM 才能产生成功 done。

入口和 RUN 共用一个 `u_s_ctrl`；不存在第二个普通 S writer。正常完整帧共 16 笔普通 S 事务：入口 8 写、结果 4 写、T_FILL 4 读。RUN 自身为 8 笔。完整 RUN 有 7 次 M 命令/响应：CLEAR、SCALE、EXEC 和四个 op3。

## reset、abort 与背压

| 情形 | 行为 |
| --- | --- |
| reset | 清帧、helper/native/service/mother 控制和有效位，不生成 completion，不保证 RAM payload 回滚 |
| prestart abort | 丢弃部分或已存储未 start 的帧，清 marker，协调 reset 叶端，无 done |
| RUN abort | 叶端/helper/service 协调 reset，母控转为一次 error DONE 并保持到消费；已被外部消费的输出前缀不能撤回 |
| 已经 DONE 时 abort | 保持原 done_valid/done_error；若同边沿 done_ready=1 则消费一次，不重复产生 completion |
| out stall | T holding payload/index/last 保持，直到 ready 或显式 reset/abort 取消 |
| done stall | 母控保留 completion；即使 abort 仍不撤回已有 done_valid 或改写已有结果 |

沿用 P2 内部信号、模块层级与强制点。`permit_m_cmd/permit_m_rsp/permit_load/permit_s_rsp` 和新增 `permit_s_req` 在硬件恒为 1，只供 TB force；S native ACK 的 valid/take 对称门控保持。`permit_s_req` 阻挡 helper 请求时，捕获的入口地址、canonicalized 数据和 index 保持稳定。

## 验证边界

本 agent 只做源码构造与静态自查，不启动 RTL 仿真。独立 TB agent 与 root runner 执行 ModelSim 并记录其真实源码 SHA、工具、命令、结果。预期必须覆盖不同输入 oracle、非零脏 padding、8 次真实 ACK、输入/输出/done 背压、两帧无旧 marker、各阶段 reset/abort 和 T release。原 P2 文件应逐字节保持不变。

`build_w1_draft.py` 只用于本目录从只读 P2 源确定性生成这两份候选，不是产品运行时工具，也不应被描述为硬件编译器。正式交付以两份最终 RTL 的字节 SHA 及独立测试回执为准。
