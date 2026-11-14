# 同一请求的指令索引与 Algo2 布线输入

远端作业 111294 从同一个 Block V2 候选底座和保存的全图请求生成指令索引与上层布线输入。索引覆盖 184,927 页、8,273,243 次 CALL，其中 639 页有 U0 Gather 替换镜像。原母控程序、描述符表、各阶段描述符及替换镜像均在索引中登记摘要。原请求包仍是其他页的指令来源。

Algo2 的原生 `verify_handoff` 已读回同计划的 6,395 个信号成员、5,935 根候选网和 12,330 个端点。输入同时包含 P0/P1/P2/U0 与 MC 和交换器的命令/返回线、三 P 的描述符/权重/fence 路径、U0 的 Gather DMA 路径，以及 C0→U0 索引传输。静态网格检查在所有端点上找到了候选接入点。联合搜索随后要同时满足接入占用与布线约束。条目中保留 C0 索引生产端尚未绑定的条件。

| 产物 | SHA-256 |
| --- | --- |
| Algo2 输入 `algorithm2-input.json` | `73f1d906fb69f78ec51b9281f4b965b83280d4e7c2603283a68941f778d6bd17` |
| 指令索引 `program.json` | `3307870b3a09b992fbad88bcab62f72f8d36780d51292571c31a0421748cdc52` |
| 布线需求 `requirements.json` | `cd16fa7deab9b8a6b752c8414440acc9924487ffde6fd8f146d8abc2a61e9c45` |
| 主底座 Gather 母控镜像 | `123608951d0af0da552aba02c51db2e9b9e9193e5356a9a135028025ac042d1d` |

## Gather 的母控与局控拓扑

原替换母控沿用了 U0 旧局控的拓扑号 `0x02500031`。联合交接使用底座登记的母控拓扑 `25001`，由现有 U0 帧桥保留旧局控拓扑和镜像格式。变更只写入母控镜像的拓扑字段。作业 111292 在两种 ACK 条件下从新镜像执行实际 MC CALL，经交换器、U0 局控、SRAM、DMA，共确认读写各 8,208 B。正常与延迟 ACK 的索引提交分别为模型第 38,802、38,811 拍，完成回包均在 41,305 拍。这个回归从归档 logits 生成索引。带同一母控镜像的真实权重词表重算回归另由作业 111303 执行。

两项负对照拒绝了混用拓扑的程序与已重绑母控镜像被当成原文件的情况。项目结构检查在远端通过。使用 PR 当前版本的检查工具和远端已存的完整管理结构目录。

## KV 指令覆盖

远端 111352 把同一个指令索引和其底座摘要绑定到独立的 KV 计划。128 个阶段的图摘要逐项一致。每条 KVR1 描述符核对 CRC、K/V 类型、DDR 行地址、阶段和相应的写区域。每个流内的 639 行连续出现一次。全量共 144 条流，46,008 个 K 行、46,008 个 V 行，共 47,112,192 B。阶段 0 涵盖 512 个 prompt 位置，其后 127 个阶段各追加一行。回执 `kv-111352.json` 的 SHA-256 为 `e0b37384733213dd14c4e63495250c3a62e70222ccfb0df1fcad54b4e128b886`。负对照拒绝了重复行、错误 CRC 和缺失写区域。它证明指令侧覆盖和预期 ACK 数。实际写入与读回仍要由正式执行提供。

## 延续正式验收

已登记候选物理服务的记录覆盖 4,417,407 次 CALL，这个计数来自路由/部署清单。仍有 14 类、3,855,836 次 CALL 缺精确的已登记派发或完成接口，其中包括 KV 相关接口、其他 P/U 服务和词表提交。词表到 Gather 的 127 条依赖仍需同底座的实时生产端。MC 有 32 位 READY 标量并可存入寄存器。P0 现有局控只发完成/错误，完成包的标量字段要求为零。请求退休还依赖正确的阶段号与活 KV 完成，不能用一个写进完成帧的 token 跳过。

`publish_native_request_handoff.py` 使用输入里的目标 ID、服务签名、完成语义、线路模板与已放置端点。当前配置是 Qwen2.5-3B 请求及此底座的 Gather 重绑规则。更换模型需要精确的 lowering、服务及其物理接口。这里的程序索引和路由接口报告不代替整个九宏执行，也不产生合格的 P512/D128 tok/s。

## 远端入口

工作目录为 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/framework-20261114-akeox2em/full-graph-zwl0Tr/merged-bmMd5X/native-request-6WI0tH/framework-r11-CatJ8r/p-native-audit-FMPaww/live-vocabulary-CgSH5M/joint-placement-CrmPRH`。交接产物位于 `handoff-111294`；以 `algorithm2-input.json` 和同目录 provenance 文件运行 Algo2 `--handoff`。作业 111290 对字节相同的输入做了有界搜索。5,935 根网中有 2 根通过几何检查，5,913 根用尽搜索预算，另有 20 根在尝试中未找到网格接入。该结果是部分布线，保留逐网诊断供 Algo2 继续。路由结果 SHA-256 为 `d87598418bf4c9e44873b165dffaf5aca7a1b7da84dcaf8f230a5dd16341e91f`。主控镜像对照位于 `gather-topology-111292`。使用 `request-handoff.sbatch`、`gather-topology.sbatch`、`live-gather-topology.sbatch` 与 `request-kv-program.sbatch` 复现。模型、走线数据库和日志均留在远端。

## 候选底座独立读回

远端 111873 用冻结版本的 Algo2 接口直接接收 `algorithm2-input.json`，并用 Algo1 的分块底座读取器从原始候选底座重新绑定网和 M10 矩形。5,935 根候选网和 12,330 个 M10 端点一致，六份接口及程序文件与 111294 逐字节一致。篡改端点坐标再重算入口摘要以及换用另一底座这两个用例均被拒绝。新导出在 `summary.json` 保存 `candidate_readback`，SHA-256 为 `d8458a826582678e089cff397a66233f64d156e2cf5dc2cfc91ce9d9033307ee`。候选底座采用分块物理视图，进入 Algo2 时继续使用 `--handoff`。

先用本项目 `block_synthesis` 和 [Algo2 PR #259 的固定版本](https://github.com/rayggxia-workspace/LLMHardwareDesign/commit/4ebd2a2fc845ccc6a1c17ed1751f208bb5791a8f) 的 `upper_router` 设置 `PYTHONPATH`，再运行 `verify_candidate_algo2.py <handoff-dir> <candidate-base.json>`。111873 使用生成交接时的独立输入 `geometry-110384/base.json`。读回结果适用于当前候选底座及其已有路由需求。产品路径仍有 14 类接口未绑定。

111882 从同一路由规范和 111290 的路由几何重算候选落点。20 根报告缺接入的网各有一个端点的唯一合法落点被已布线路占用，空网架上均可落。受影响为 P2 描述符 17 根、P1 fence 1 根、P0 控制 2 根。这个结果把诊断定位到试布占用。路由器保留非硬约束分类。复现用 `request_retirement/route-input-survey.sbatch`。回执 `route-survey-111882.json` 的 SHA-256 为 `c5125d6d5e0362befe6995cbc00d859798044d083c72881292c659b662d5beb1`。两项产物位于上述工作目录的 `algo2-readback-gu7sOs3Z`。

## C0 的 S32 残差编译与搬运接口

远端作业 111950 读取 Qwen2.5-3B 第 0 个输入位置、第 0 层 `/model/model/layers.0/Add_1` 的封存算子计划及 ADD2 描述符。选择 C0 的 S32 E32 服务，将 8 KiB 输出展开为 512 条 16 B 局部加法和 32 个局控镜像。原始计划在 U0 执行并含两次 DDR 读入。此实验显式要求两份输入已经在 C0 的 16 KiB 私有 SRAM 中，因此重新编译的是计算片段。每条 `L_EXEC` 后跟 `L_WAIT`，最后由局控报告任务完成。Algo2 独立复核该片段的 431 根控制网及 863 个 M10 端点。损坏指令描述符 CRC、改变操作数地址、换用其他 SRAM 三个对照均被拒绝。

C0 的 128 位 `rx_data` 在源 DEF 中有 128 个 M10 接点。U1 源 DEF 的 128 位通用 `outgoing_data` 无 M10 接点，U0 暂存放置的接点清单也无此总线的 M10 接点。现有反向 C0→U0 索引搬运需求有 153 根已绑定候选线，包括数据、地址、接纳、存后确认与目的地预留信号。该需求来自原整图交接。残差结果在进入原请求之前仍需分配出入窗口、搬运及母控等待。

PR #260 的模型在 S32 相加溢出时拒绝写入。C0 E32 指令可返回饱和状态。等价范围限定为各 lane 的和均落在 S32 范围内。此次检查覆盖机器记录和端点绑定，数值回归与母控执行待验收。

复现在上述工作目录的 `residual-c0-PABZ4Gwh`，以 `resident.sbatch` 运行。源码和配置位于 `resident_s32/`。`c-e32-profile.json` 固定候选 C 网表、已归档的 RTL 证据及局部拓扑。复现时将该配置的 `rtl_archive_commit` 和 `rtl_archive_path` 指向的 Git 内容保存为配置目录下的 `rtl_witness`。远端复核使用 Algo2 固定版本 `4ebd2a2fc845ccc6a1c17ed1751f208bb5791a8f` 及 `issue250-u-n32-stored-link-20261112-01/staged/project/control_image_v0_1` 中的二进制编解码器。

| 产物 | SHA-256 |
| --- | --- |
| `resident-111950/residual-proof.json` | `95aea6c6877a8b0b9a3b0da4ef57a648d1a6a2133c798211b9343b1c7cc4a3d5` |
| `resident-111950/algorithm2-input.json` | `1e114e23e85fca0f38c2dda1631e337ebdf5023a2ef388bf490bdcdc39e39de3` |
