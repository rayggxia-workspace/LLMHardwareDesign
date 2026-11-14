# 同一请求的指令索引与 Algo2 布线输入

远端作业 111294 从同一个 Block V2 候选底座和保存的全图请求生成指令索引与上层布线输入。索引覆盖 184,927 页、8,273,243 次 CALL，其中 639 页有 U0 Gather 替换镜像。原母控程序、描述符表、各阶段描述符及替换镜像均在索引中登记摘要。原请求包仍是其他页的指令来源。

Algo2 的原生 `verify_handoff` 已读回同计划的 6,395 个信号成员、5,935 根候选网和 12,330 个端点。输入同时包含 P0/P1/P2/U0 与 MC 和交换器的命令/返回线、三 P 的描述符/权重/fence 路径、U0 的 Gather DMA 路径，以及 C0→U0 索引传输。所有端点在声明的候选网格中有接入点。接口准入只说明端点、方向、网和来源一致，详细走线由 Algo2 执行。条目中保留 C0 索引生产端尚未绑定的条件。

| 产物 | SHA-256 |
| --- | --- |
| Algo2 输入 `algorithm2-input.json` | `73f1d906fb69f78ec51b9281f4b965b83280d4e7c2603283a68941f778d6bd17` |
| 指令索引 `program.json` | `3307870b3a09b992fbad88bcab62f72f8d36780d51292571c31a0421748cdc52` |
| 布线需求 `requirements.json` | `cd16fa7deab9b8a6b752c8414440acc9924487ffde6fd8f146d8abc2a61e9c45` |
| 主底座 Gather 母控镜像 | `123608951d0af0da552aba02c51db2e9b9e9193e5356a9a135028025ac042d1d` |

## Gather 的母控与局控拓扑

原替换母控沿用了 U0 旧局控的拓扑号 `0x02500031`。联合交接使用底座登记的母控拓扑 `25001`，由现有 U0 帧桥保留旧局控拓扑和镜像格式。变更只写入母控镜像的拓扑字段。作业 111292 在两种 ACK 条件下从新镜像执行实际 MC CALL，经交换器、U0 局控、SRAM、DMA，共确认读写各 8,208 B。正常与延迟 ACK 的索引提交分别为模型第 38,802、38,811 拍，完成回包均在 41,305 拍。这个回归从归档 logits 生成索引。带同一母控镜像的真实权重词表重算回归另由作业 111303 执行。

两项负对照拒绝了混用拓扑的程序与已重绑母控镜像被当成原文件的情况。项目结构检查在远端通过。使用 PR 当前版本的检查工具和远端已存的完整管理结构目录。

## 延续正式验收

已登记候选物理服务的记录覆盖 4,417,407 次 CALL，这个计数来自路由/部署清单。仍有 14 类、3,855,836 次 CALL 缺精确的已登记派发或完成接口，其中包括 KV 相关接口、其他 P/U 服务和词表提交。词表到 Gather 的 127 条依赖仍需同底座的实时生产端。MC 有 32 位 READY 标量并可存入寄存器。P0 现有局控只发完成/错误，完成包的标量字段要求为零。请求退休还依赖正确的阶段号与活 KV 完成，不能用一个写进完成帧的 token 跳过。

`publish_native_request_handoff.py` 使用输入里的目标 ID、服务签名、完成语义、线路模板与已放置端点。当前配置是 Qwen2.5-3B 请求及此底座的 Gather 重绑规则。更换模型需要精确的 lowering、服务及其物理接口。这里的程序索引和路由接口报告不代替整个九宏执行，也不产生合格的 P512/D128 tok/s。

## 远端入口

工作目录为 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/framework-20261114-akeox2em/full-graph-zwl0Tr/merged-bmMd5X/native-request-6WI0tH/framework-r11-CatJ8r/p-native-audit-FMPaww/live-vocabulary-CgSH5M/joint-placement-CrmPRH`。交接产物位于 `handoff-111294`；以 `algorithm2-input.json` 和同目录 provenance 文件运行 Algo2 `--handoff`。作业 111290 对字节相同的布线输入做了有界搜索。主控镜像对照位于 `gather-topology-111292`。使用 `request-handoff.sbatch`、`gather-topology.sbatch` 与 `live-gather-topology.sbatch` 复现。模型、走线数据库和日志均留在远端。
