# Shared A 32 B/P/cycle 静态复核

日期：2026-11-10。任务：Issue #247 下共享 A 原生接口由 1 个扩为 2 个 128-bit 容器/拍。复核人：`shared_s_schedule` 子代理；根代理负责正式集成、提交与服务器验证。

本记录仅为源码静态复核和定向测试设计，**未执行 EDA 编译、仿真、综合或物理验证；不是正式 PR 批准**。功能、周期、默认兼容性和面积结论等待服务器 Slurm 回执，不据此宣称整图 token/s。

## 范围与身份

- 本代理独占目录：`work/Melodydt/247/a32-rtl/pool`，分支 `task/247-a32-pool`。本地源子集基线 `6cf0981c6612fe5c7a7a6b8e20106d7c5b93b2e4`；上游身份由 `BASELINE.json` 指向 `2fc03de589e65f28d362128f9d988034429fd50c`。
- 本代理改动仅为 `shared_a_pool32.sv` 和新增 `tb_a32_control.sv`。对相邻 `operands`、`tests` worktree 的检查均为只读。
- 工作区缺少管理脚本，未在源子集中补造脚本；根代理报告正式仓库管理检查已通过。本记录的直接检查为文本阅读、接口/状态推导、SHA-256 和 `git diff --check`，后者通过。

## Pool 与 FIFO 信用

`A_WORDS_PER_BEAT` 支持 1/2，默认为 1；P-major、lane-major 索引为 `P*A+lane`。双词仅来自同一 64-byte FIFO 头的相邻 128-bit 容器，允许 cursor=1 取词 1+2，禁止跨 FIFO 头拼接；cursor=3 或剩余单词输出 `01`，其余双词输出 `11`，共享 ready 原子接受全部有效词。

- 发送数、cursor、row/tile 和完成判定按实际接受的词数推进。两次独立 wrap 推导覆盖 rows=1 的同拍两次换 tile；最大 32 词时 `30+2` 不溢出 6-bit 计数。
- 背压下 mask/data/tags 由同一未弹出的头和未推进状态驱动，保持稳定。没有新增缓存或 FIFO 信用。
- 原约束 `fifo_count + pending_owned <= 4` 保留。满 FIFO 时 pending=0，因此未弹出的满队头不会被返回覆盖。返回与弹出同时发生且原队列非空时，原 count<=3，tail 与 head 不同；原 count=0 则没有有效弹出。满队列弹出释放的位置可供随后返回，当前 head 已前进。
- 全局单路读仲裁、8 个 SRAM 宏、初始化写和 fill ACK 逻辑未改变。默认 1 词分支的状态推进、低 lane 数据/标签和握手组合关系与旧逻辑一致；逐周期等价仍须仿真回归。

## M、P 与 pair 接口

只读检查 `operands` 中两个 M、`pu_p_group` 和 `pu_p_shared_pair`：

- M 对高 lane 单独有效的 `10`、双 lane 重复 `{row,tile}` 统一令 ready=0；两 lane 在同一握手下写入，distinct tags 保证地址不重叠。静态循环/索引未发现明显综合障碍，实际 Yosys 接受情况仍待验证。
- clear-all、clear-bank、START 同执行 bank 和运行中锁定 bank 的拒写门控保留。op6 清有效位，并不要求清 payload/format；op11 按 bank 位清有效位，允许另一 bank 的合法写。
- P 共享入口传递全部 lane；本地 feeder 仅使用低 lane，其余无效且置零；feed-empty 使用 valid 的归约 OR。B hold 和 M 算术路径未改。
- Pool/M/P 的参数默认值为 1；pair 的默认值为 2。兼容性用例必须显式选择 pair=1，不能把 pair 不传新参数描述成旧行为。生成器已为 candidate16 显式指定 1。

## 新控制测试

`tb_a32_control` 在 CONTEXTS=0/8 下使用真实 M 和真实 ready/valid。只读层级观察 aa/av/af/locked，不以替代模型声称算术验证。

覆盖 op6 同拍拒写、op11 同 bank 拒写/另一 bank 双写、合法 START 同 bank 拒写、运行中另一 bank 双写、bank1 S8/S16 payload、`01` 尾拍高 lane 垃圾不写、reset 拒绝 ingress/清有效与格式位，以及复位后旧描述符因标签无效被拒绝。合法双写任务数固定 5；其余 7 个定向覆盖计数各为 1。所有响应还检查背压下稳定。

静态检查确认合法 START 前 A/B 已就绪，busy-other 在实际 locked 时接受，op6 没有错误要求清 aa/af。`shared_s_rtl` 对冻结版额外只读复审，未报告阻断。测试仍待服务器执行。

## 测试生成器与性能口径

- pool 派生 bench 保留旧满 FIFO/8 次读暂停、背压、掩码、无广播、非法描述符、释放和 reset 检查，新增 rows=1/3/7/8、tiles=1..4、起点=0..3 的 64 组双 P 随机 ready 用例；每 lane 单独核对值、地址和标签，stalled 快照包含完整 mask。
- pair 微基准在相同 CONTEXTS、格式、rows、tiles、lastK、base、A 容器数、命令数、数值检查数和 checksum 下比较 1/2 词。初始化周期与 M 计算周期要求相等，其他非计时字段逐项相同。
- `processing_cycles` 是双 P 发起 LOAD 后，直到双方 LOAD、M 计算、结果读回、固定 ACK 等待和 context 释放结束的墙钟周期。它排除池配置/填充/seal、B 初始化及末尾 pool RELEASE。`cycles` 包含初始化和处理，但同样不含随后 RELEASE。
- `load_cycles`、`compute_cycles`、`feed_span_cycles` 是两 P 各自区间之和，存在重叠，不能相加当墙钟分解。runner 使用 processing 墙钟总和计算微基准 speed_ratio，显式 `no_token_s_projection=true`。
- 不能用此比率直接倍乘旧条件模型 token/s。此测试不是完整网络调度，也没有 DDR、完整输入生产、持续跨 op 调度或物理频率证据。
- 发现 required manifest 集合未强制包含实际 include `block_v2_g_tables.svh`，已通知测试负责人；重新读取确认现已显式加入。未修改对方文件。

## 已读源 SHA-256

| 所在 worktree / 文件 | SHA-256 |
|---|---|
| pool / `project/rtl/shared_s/shared_a_pool32.sv` | `ef5d3234f4ff3685705077f701aa8806dbcb680cb8c0cd940ee072db31debade` |
| pool / `project/experiments/shared_a32_native/tb_a32_control.sv` | `a8faa2d9f9f8e264e529ac04f1fea8837ae6907c39f423a01fde7c249efc398e` |
| operands / `project/rtl/block_v2/block_v2_m.sv` | `3c5c776f92895924fd338ec5a73fa18b00022f991bcdb2fb556dcc47470d72c8` |
| operands / `project/rtl/block_v2/block_v2_m_context.sv` | `2f0815b577f5e4c2962125b842b3217e28f577623c18bd95244bca9528e514a7` |
| operands / `project/rtl/pu_leaf_base/pu_p_group.sv` | `f8699191dff0cce43980aa1e893b9c76810bae682ccbfbbecc75176afaa67a8f` |
| operands / `project/rtl/shared_s/pu_p_shared_pair.sv` | `7db82dfb2795d742c15d2beb1446d350b5dab01ffae182fb9deac2d051c62cb9` |
| tests / `project/experiments/shared_a32_native/run.py` | `2eacc2a3108ac814021da48363aafa395eaf355631bf30a106849942f335037b` |
| tests / `project/experiments/shared_a32_native/generate.py` | `e4c1dfaa6f94e840cf8edcbd105ca82bddfd181115613f3d7a1c39c7b3681ce5` |
| tests / `project/experiments/shared_a32_native/pair_body.sv.inc` | `f79805dfdc6facb82ba9e4492cdb4d87685956658136d36f74fd5723b60b7233` |

上述为复核时实际文件字节身份，不替代根代理最终集成 commit 与运行 manifest。若源后续改变，须核对差异后再沿用本结论。

后续：根代理提交服务器 Slurm；回收后核验实际日志、默认 1 词逐周期回归、三个 reset/seed 组合、数值/覆盖与周期守恒，以及面积报告的宏数和统计范围。当前未发现静态阻断，但不预判工具与功能结果。
