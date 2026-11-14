# U0 Gather 候选

Issue #219，PR #269。该目录记录一个 Block V2 U0 原生服务的局控编码、目标 SRAM 提交、候选 M10 端点和 Algo2 接口试验。产品验收仍使用固定 PR #260 全请求入口。

## 远端复跑

在 FRAMEWORK_INTEGRATION 记录的证据目录中运行。所有 Slurm 脚本的第一个参数是本目录。其余路径使用框架目录、相应封存版本和已经验证的前置作业输出。

1. 从 `ingress-route-iN0LbH/source/u` 复制 `u_n32_controlled_64.sv`、`u_n32_legacy_dispatch.svh` 和 `wrapper.sv`。用 `sha256sum -c original-u.sha256` 核对，再运行 `python3 integrate_u_gather.py`。程序级断言还需要证据目录的 `block_v2_e.sv`，SHA-256 为 `865ff289b05c5bcd045ae4bc40feeb9402b928b281951367c31e8c4c2c752b0b`。
2. `contract.sbatch WORK FRAMEWORK DMA_BASE_JSON` 独立核对原生程序和原接点缺口。`lower-request.sbatch WORK FRAMEWORK INDEX_AUDIT_DIR` 批量核对已封存的 639 个 Gather。
3. `run-program.sbatch WORK FRAMEWORK INGRESS LOCAL_PM` 检查真实局控和 SRAM。运行 `python3 build-frame-test.py` 生成四拍接口用例，再用相同参数运行 `run-frame-program.sbatch`。权重行从实际封存文件读取，DDR 后端由测试端驱动。
4. `map-frame.sbatch WORK FRAMEWORK INGRESS` 综合带外层接口的 U0，保留签名中的一块程序 SRAM 和 N、E、S 叶宏。`stage-frame.sbatch WORK MAP_DIR U39_DEF` 约束外形、叶位置和已有信号端点。独立端点审计使用 `audit-frame.sbatch WORK PLACE_DIR FRAMEWORK`。详细布线诊断用同样参数调用 `route-frame.sbatch`。
5. `handoff.sbatch WORK FRAMEWORK DMA_EVIDENCE_DIR PLACE_DIR STAGED_PORTS_TSV` 从同一计划导出局控字节和候选线路。`try-algo2.sbatch WORK HANDOFF_DIR UPPER_ROUTER` 用现有 Algo2 试布入口消费接口包。

[作业与散列](../../FRAMEWORK_INTEGRATION.md#u0-gather-的局控程序和两端布线交接)

## DDR prompt 与 decode 索引入口

在同一远端试验目录执行 `python3 build-frame-test.py`，再运行
`patch -p0 < prompt-frame.patch`。执行
`run-prompt.sbatch WORK FRAMEWORK INGRESS INPUT_INDEX_TSV LEGACY_PM ARCHIVE_CHECKER`，
其中后两个输入分别为已确认的 SRAM 索引版 PM 和归档定位脚本
`check-native-ingress.py`。脚本重读并验证第 0、16 页的封存计划。
Prompt 绑定把字地址直接编码进 PM，v45 客户端 3 取一个对齐的 128 B 记录。
保留原 SRAM 索引的兼容测试。返回的数据来自封存资产，DDR 时序由测试端驱动。

`lower-request.sbatch` 对模式 1 编码真实 prompt 地址，对模式 2 记录前一
退休步、目标字和 lane 的确认依赖。模式 2 仍需母控接到 U0 的真实写入提交路径。
