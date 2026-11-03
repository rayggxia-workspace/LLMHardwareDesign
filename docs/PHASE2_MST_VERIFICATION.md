# P2 独立 RTL 验证报告

本文件由独立验证准备报告整合发布；下述本地批次路径保留实际来源。正式文本日志与回执已复制至work/Melodydt/151/phase2-rtl-evidence/，源码/日志SHA在根任务检查中读回核对；远端提交、Issue/PR/看板状态以PR152回执为准。

日期：2026-11-01（Asia/Shanghai）。任务 Issue151 / PR152，负责人 Melodydt。研究输入为 `be10e69bb9ad625079f68361fb47b4747d6ce040`；本轮叶源固定最新选定 PR144 `707878621b2add4ed218b8c43df2e95c9a56e2ba`，由根任务同步与登记 source-lock。本子任务只写 `drafts/verification/` 及根任务明确指定的 `final-rtl-run/`，不修改叶宏、其他成员源码、正式 integrated 包或远端；无 SSH/远程计算。

**实际结果：正式目录的14核心源码编译门通过，S_CTRL 与最小 MST 的两个真实 SystemVerilog testbench 通过，共19个 CASE_PASS 标签。** 这是 RTL 功能测试，区别于 P1 Python 参考与静态检查；不是全部连接/算子/形状、完整模型或物理验收。

## 1. 环境、执行与证据位置

实际工具为 `D:/EDA/modeltech64_2020.4/win64/{vlib,vlog,vsim}.exe`：

- `Model Technology ModelSim SE-64 vlog 2020.4 Compiler 2020.10 Oct 13 2020`。
- `Model Technology ModelSim SE-64 vsim 2020.4 Simulator 2020.10 Oct 13 2020`。
- runner：CPython 3.7.0，Windows 10 build26100，仅标准库；无安装、PATH 修改或外部工具下载。

首次沙箱内 `vlog/vsim -version` 在启动前遇到 Windows DLL 重定位错误。依据用户本轮本地 RTL 仿真的明确授权，经工具审批改用沙箱外执行，版本查询、编译和仿真均可正常运行。没有读取 license/凭据内容，没有修改安装目录或系统配置。runner 在独立输出目录生成最小 `modelsim.ini`，没有读取/复制安装配置。

已执行三个本地批次：

| 批次 | 位置 | 实际结果 |
|---|---|---|
| 环境 smoke | `drafts/verification/runs/environment-smoke-01/` | 一个独立 SV module 经 vlib/vlog/vsim，`PASS_P2_ENVIRONMENT_SMOKE`；仅确认工具可执行 |
| 首轮真实组合 | `drafts/verification/runs/mst-all-01/` | 14核心源编译 + helper/MST 两个 TB，19 CASE_PASS |
| 正式路径复跑 | `final-rtl-run/` | 读取 integrated 正式 RTL/TB/runner 默认路径，以相同源码 SHA 再编译/仿真；19 CASE_PASS |

正式复跑起止 UTC 为 `2026-11-01T06:43:33.329400+00:00` 到 `2026-11-01T06:43:37.473986+00:00`（来自实际 `run-receipt.json`）。每个 vlib/vlog/vsim 原始退出码均保存于回执。编译摘要 `Errors:0, Warnings:0`；两个仿真均实际 exit0 并包含所需 PASS token。ModelSim Tcl 输出有 `onbreak/onerror command for use within macro` 提示；runner 不单凭退出码或摘要判成功，还要求 PASS token 存在且没有 FAIL_P2/Fatal。它们不被当成 DUT 错误，也没有为通过测试修改有效断言。

根任务可仅上传下列文本证据，不上传 ModelSim work 库、二进制、WLF 或 source 快照：

```text
final-rtl-run/run-receipt.json
final-rtl-run/compile.log
final-rtl-run/simulation-helper.log
final-rtl-run/simulation-mst.log
final-rtl-run/vlog-version.log
final-rtl-run/vsim-version.log
```

`run-receipt.json` 记录实际 argv、工作目录、开始/结束时间、原始 stdout SHA、UTF8/LF 文本日志 SHA、工具版本与可执行文件 SHA、每个输入源/TB/runner/fixture 的 SHA256 与 Git blob SHA1、CASE 标签及资格边界。日志文本规范化为 UTF8/LF，另记录规范化前 stdout 字节的 SHA；不把两种 SHA 混为原始同一文件。

## 2. 最新14核心源码的编译门

runner 读取 `work/Melodydt/151/phase2-source-lock.json`，要求 selected ref 为上述7078786、共14条；对每份实际文件同时核对 SHA256 和 Git blob SHA1，再复制到本次输出的 source 快照。12份 `.sv` 传给 `vlog -sv`，两份 `.svh` 从同一快照目录经 `+incdir` 被包括，不把 include 当独立顶层 module。

本门涵盖 M/N/E/G/R、N group、S storage/loader/macro、T 及锁定列表中的旧 feed/shared 源。**N/E/G/R 和旧模块本轮只有语法/解析编译，不宣称功能仿真或新物理资格。** 最新 R SHA256 为 `4032c5edcbee9d38e1a51dd9f9c533e414d5263dd2440d7104a1688e73ca382d`，成功编译不构成 R 数值等价、周期行为、质量或最终物理接收。M/S/T 源字节与 P1 643c6012 一致。

## 3. 独立 S_CTRL testbench

文件 `phase2_s_ctrl_tb.sv`，真实实例化新 `block_p2_s_ctrl` 和原生 `block_feed_s16k`。TB 在握手两端对称插入请求/应答许可，不改变载荷，独立 literal 写入/读回预期；请求被 helper 接受后立即改动上游字段，检查 helper 确实锁存。未使用 mock S 来代替原生读写/ACK。

| 标签 | 实际检查 |
|---|---|
| H01_CAPTURE_REQUEST_BACKPRESSURE | 原生请求被阻塞数拍，地址/写标志/data 保持，上游改字段不影响已接受请求 |
| H02_NATIVE_WRITE_ACK_AND_READBACK | 写 ACK 返回新 din，覆盖旧值时仍等于新 din；随后真实 S 读回一致 |
| H03_RESPONSE_HOLD_EXACTLY_ONCE | 延迟原生 ACK 接收及 generic 响应接收；持有数据/valid，每个完成事务恰好一请求、一 ACK、一响应 |
| H04_RESET_BEFORE_NATIVE_ACCEPT | 请求锁存但尚未被 S 接受时协调 reset，queued write 被取消，旧 payload 保留 |
| H05_RESET_AFTER_WRITE_PRESERVES_PAYLOAD | S 已接受写、ACK 尚未消费时协调 reset；旧响应清除，但已写 RAM 不回滚，后续读回新值 |
| H06_REPEAT_TRANSACTION | 多次写/读后仍能接受下一事务，没有多发或丢失普通响应 |

实际仿真 **141 个上升沿**、8个完成事务。每个正常完成事务单独检查 generic request/native request/native ACK/generic response 全部加1。总体计数 gr10/native_req9/native_ack8/generic_rsp8 的差额来自两个明确的 reset 用例：一个在 native accept 前取消，一个在 accepted write 后丢弃未消费的 ACK；不是正常事务静默丢 ACK。native S 没有错误端口，helper `rsp_error=0` 的边界保留。

## 4. 最小 MST testbench

文件 `phase2_mst_tb.sv`，直接实例化新 `block_p2_mst_top`，内部使用真实 S macro/loader、M v2、T 与新 helper/mother ROM。仅固定 P2_S8_DOT8_RAW64：S8×S8、rows1、tiles1、K8/N8、bank0、factor1/left0；A448..451、B452..455、result456..459。独立 literal 的四个完整128bit预期为：

```text
fffffffffffffff8fffffffffffffffc
fffffffffffffff0fffffffffffffff4
ffffffffffffffe8ffffffffffffffec
ffffffffffffffe0ffffffffffffffe4
```

TB 自己保存这些固定值，不调用 DUT 的 `initial_word` 或 Python M 运算生成期望。fixture 仍为 P1 JSON（SHA `d2b5022530f73eb11756f633be17fe0f13cb30ce3752af6a2bd4499996efc18e`），runner 记录其指纹；本 TB 不把 JSON 全部其他数值例动态编译成 RTL case。

| 标签 | 实际检查 |
|---|---|
| M01_LITERAL_S8_DOT8_END_TO_END | 初始化、loader、SET_SCALE/EXEC/op3、S结果写回、T填充/提交/4字输出/释放，literal 全包相同 |
| M02_ACK_OWNER_AND_LOAD_VS_EXEC_DONE | 普通 S 请求与写/读 ACK 归属；loader done 先完成且不等于 M done；EXEC 不提前；逐批计数核对 |
| M03_NATIVE_RESPONSE_AND_OUTPUT_STALL_HOLD | 真实 M response、S ACK 与 T 输出反压时 data/sideband/valid 保持；输出 index0..3/last 只在末字 |
| M04_BUSY_START_REJECTED_AND_DONE_HOLD | busy 中 start 脉冲不排队第二任务，done_ready0 时完成状态保持 |
| M05_REPEAT_RUN_SAME_LITERAL | 完成后再运行相同固定程序，得到同一四包 |
| M06_ABORT_WITH_EXISTING_DONE_TAKE_NO_DUPLICATE | DONE 已存在时 abort+done_ready 仍消费已有完成，之后回 IDLE，不重复/吞掉完成 |
| M07_RUN_ABORT_FLUSHES_PENDING_ACK | RUN 中真实 S ACK 尚未消费时 abort，同拍协调 leaf/helper reset，产生 retained error completion |
| M08_RECOVER_AFTER_ABORT | 消费 abort 完成后可重新运行成功 |
| M09_HARD_RESET_AT_T_STALL | T首个已提交输出被阻塞时 hard reset，停止输出/完成并清生命周期；已接受任务不凭空补完成 |
| M10_RECOVER_AFTER_HARD_RESET | hard reset 后重新初始化/执行成功，没有旧输出或旧 done |
| M11_NATIVE_EXEC_DESCRIPTOR_ERROR_PROPAGATION | 只在一拍 EXEC 接受前 force reserved bit，真实 M 返回 error；顶层不发布结果、产生错误完成 |
| M12_NATIVE_LOADER_ALIGNMENT_ERROR_PROPAGATION | 一拍将 loader A base force 为449，真实 loader 拒绝对齐，顶层不执行 M、产生错误完成 |
| M13_RECOVER_AFTER_NATIVE_ERROR | 消费原生错误完成后重新运行成功 |

这13项是一个 TB 进程内的检查标签，不是13个独立工具进程或全角色覆盖分母。force 只用于测试中双方一致的许可门或一拍原生非法字段；没有 force 正确计算结果、完成状态、RAM输出或 scoreboard，也未修改叶宏以得到 PASS。

MST 实际仿真 **1101 个上升沿**。五个正常完成批次都逐批断言：16次普通S请求=16个ACK（12写/4读）、7个M命令=7响应、1次loader接受=1次done、A/B各1 beat、T BEGIN1/WRITE4/COMMIT1/READ4/RELEASE1。输出每包都在真实 out_valid&&out_ready 时比较 literal/data/index/last，停顿期间也比较保持。

全进程汇总 Sreq113/Sack112、Mcmd49/Mrsp49、Tread20。少1个S ACK是 M07 中被明确 abort 掉的已接受写，和 helper reset 用例一样不承诺 RAM回滚。不能把总体计数差额描述为正常路径无条件丢响应；所有正常批次的对账都严格相等。

## 5. 可复现命令与 runner 行为

正式 checkout 中保持以下布局：

```text
project/rtl/block_connection_p2/block_p2_{s_ctrl,mother_rom,mst_top}.sv
project/tb/block_connection_p2/phase2_{s_ctrl,mst,environment_smoke}_tb.sv
work/Melodydt/151/run_phase2_mst.py
work/Melodydt/151/phase2-source-lock.json
```

从任意该 checkout 根运行，输出必须是新目录，runner 拒绝覆盖旧日志：

```powershell
python -B -X utf8 work/Melodydt/151/run_phase2_mst.py --root . --tool-dir D:/EDA/modeltech64_2020.4/win64 --suite all --output-dir work/Melodydt/151/local-runs/p2-unique-run
```

本轮最终实际命令为：

```powershell
python -B -X utf8 work/Melodydt/151/phase2-be10e69/integrated/work/Melodydt/151/run_phase2_mst.py --root work/Melodydt/151/phase2-be10e69/integrated --suite all --output-dir work/Melodydt/151/phase2-be10e69/final-rtl-run
```

支持 `--suite native-compile/helper/mst/all/smoke`，以及显式 `--core-root/--s-ctrl-root/--tb-root` 用于隔离准备目录。`native-compile` 只做14核心编译，不启动功能仿真；`all` 编译14核心与新 RTL/TB，并分别运行 helper 和 MST。环境 smoke 仅验证工具，不加入功能19例。超时180s会使该命令失败并保存回执；TB另有时钟 watchdog。runner 记录真实工具退出码，再独立检查成功 token 与失败文本；失败不能只因工具退码0而误记 PASS。

## 6. 尚未覆盖与验收边界

本轮未运行 S16 loader/mixed precision/op5 RNE/饱和、可达 S64 溢出逐行保旧的真实 RTL 对照；这些仍只有 P1 有界整数参考，不转记为 RTL 通过。未测任意 rows/tiles/K/N、多个输入 bank、reuse_b 权重身份、M selected-bank 锁/对侧bank并行装载、loader A/B独立 sink stall/全部queue活性、S普通口与内部wide读同时仲裁、T所有非法长度/乱序索引/384字端点、R状态版本和其他宏连接。

本轮阻塞 M 命令/loader 的测试点是**启动许可门**，并未代替“native cmd_ready为0而valid仍保持”的全部情形。M response、S ACK和T输出则确实在真实 valid=1、消费受阻时检查了保持。hard reset/abort 仅采用本程序定义的协调复位，不宣称任意局部复位都安全；已接受S写、已接收输出不能回滚。

七宏语法编译不能证明七宏功能、更不能证明 R 更新合格；19标签也不是全合法连接打通率。这里没有综合、P&R、时序/功耗/面积、形式活性、完整产品ROM/模型程序、整模型量化质量、外存接口/调度或跨时钟系统验收。系统有外存，本轮小切片只不接入外存，不形成产品永久禁外存约束。后续按七步路线继续，最终审查/上传/合并/登记/看板状态由根任务统一如实交付。
