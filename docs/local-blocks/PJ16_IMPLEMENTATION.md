# P16 与 J16 的执行接口

[Issue #187](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/187) · [每轮复现记录](../../work/YUZE-LU/187/README.md)

两个 Block 各有一个同步时钟和同步高有效复位。复位进入父层寄存器后分发，清除指令、片段记录、保持槽及租约。外部控制在复位生效期间保持请求空闲，J 在切换 epoch 后用新 epoch 发请求。16 KiB SRAM 的原字可能仍存在，运行程序凭有效对象记录决定可读范围。

## P16

P16 使用各一颗 M、G 和带 feeder 的 16 KiB P4。地址以 128 位 SRAM 字为单位，共 1024 字。P 的两个外部 SRAM 客户端各有一笔在途信用，响应可停在保持槽。外部源收到真实写响应后可复用相应存储，ready 握手表示本层已接收请求。

- `load_*` 使用 P4 feeder 原生合同。A 与 B 基地址遵循四字对齐，B 宽读占用四银行。请求先进入一个保持槽，A/B 各有一个 1-credit 寄存槽。P4 回报完成且 M 已取完最后一拍后，P 才发布完成与错误状态，保持到 `load_take`。该 ACK 释放下一笔载入信用。
- `cmd_*` 使用 M 的原生命令、索引、参数和单个结果保持槽。带 `cmd_store` 的成功命令在目的 SRAM 回应后发布 `cmd_done`。原生读取把各 S16 值放入 S32 容器，`cmd_pack16` 可将四个值紧凑写入目的字。上层按所选数值 profile 提供位宽和舍入。
- `gate_*` 读两份 S16×2 数据，用 G 执行 gated SiLU，然后向目的 S 写回。完成跟随真实 SRAM 响应。上层负责任务身份、S 窗口和数据生存期，避免另一个任务覆盖被消费的对象。
- `cmd_route` 接受 S16 格式化读取，发出 `m_to_g_data[31:0]` 和 `m_to_g_valid`，发布完成后保持数据直到 `m_to_g_take`。持有期间 M 命令信用被占用。接收侧在 `gate_route` 中用独立的 `g_from_m_*` 接住这两路 S16，另一操作数及写回继续走 S。这些信号的 M10 端点对应后制候选，RTL 回归中以显式桥接开关测试。

## J16

J16 使用各一颗 E、T 和 16 KiB N4。接收侧有一个请求保持槽。RX 字经 SRAM 写响应后登记给一个分支槽，允许不同分支以任意顺序完成。分支内部是连续字序，用 `rx_last` 封口。三个槽只共享一个 J 汇合租约。 `rx_tag[31:24]` 为 epoch，低 24 位为上层分配的汇合身份，槽号区分不同分支。三个输入须是同一量纲的 S16。

- RX 通道 0 仅接受写，地址与数据分别走 `io_req_addr[9:0]`、`io_req_data[127:0]`。错误响应带 `rx_error`，调用方须检查。有效响应对应已落地的字。旧 epoch、越过连续地址、重叠分支与重复封口均拒绝。
- `start` 携带 `join_tag`、长度、目的窗口和第三分支开关。两路走 E 的原生加法。三路以 18 位中间值求和，最后按一次 S16 饱和，防止分步饱和改变结果。目的窗口允许与一个输入完全原位复用，部分重叠被拒绝。
- 每个结果字先写 S，再由 T 客户端读回并提交给 T。最多 384 字对应 6 KiB T。写完、封存后发布 `done_valid`。排出有一个保持槽，在背压下保持 `out_data`、tag、index 和 last。
- TX 通道 1 是已封存结果窗口的可选只读访问，地址走 `io_req_addr[19:10]`，读回走 `io_rsp_data[255:128]`。释放租约等待 T 排出及在途 TX 响应完成。释放后继续接收下一笔汇合。

## 复跑与证据

从任务工作树导出源码，脚本使用 LF。输入叶视图及来源 SHA-256 由 `export_leaf.py` 核对。下列脚本在任务自己的服务器目录中提交，源树、输入和每轮输出用不同目录固定。

```bash
sbatch run_leaf_views.sh "$source" "$leaf_views"
sbatch run_rtl.sh "$source" "$sram_qualified_source" "$rtl_evidence"
pnr_job=$(sbatch --parsable -n2 run_grid_study.sh "$source" "$leaf_views" "$pnr" guide-via)
sbatch --dependency="afterok:$pnr_job" run_gates.sh "$source" "$leaf_views" "$pnr/guide-via" "$gates"
```

实际配置、作业号、数据摘要与每轮限制见迭代索引。验收检查用实际最终 ODB 及展开叶宏的网表和寄生，SRAM 银行沿用已验收 TT 视图。P/J 独立交付的端点随后交给九实例底座和产品路由。[实现草稿 PR #190](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/190)
