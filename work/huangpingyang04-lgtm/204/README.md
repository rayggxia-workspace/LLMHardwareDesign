# Qwen3.5-4B 九实例上层接线审计与试布

- 任务 [Issue #204](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/204)，承接 #184。执行账号 huangpingyang04-lgtm。
- 底座使用 [#194](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/194) 提交 `6228d12ea20a2ae538c282697de1a92b1ca4d3af` 的 256 µm 纵向九实例摆位、五份验收 LEF 和 2 µm 研究几何规则。摆位来自该归档中的 `escape-97881-30/inputs.json`。LEF 和摆位的输入摘要见 [inputs.sha256](inputs.sha256)。
- 逻辑输入是 [#176 固定版组合图册第 8 节](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/08f2ea20a11dfdd09892a67599163e32b7237edb/docs/local-blocks/COMPOSITE_MODEL_FLOWS.md#8-三模型的数据路线并集与有限端点) 的 Qwen 候选映射。

## 逐位清单

Slurm `98271` 在 c64 完成。按 Attention、GDN、FFN、残差及层间交接的 23 条有向 S→S 传输关系，每条展开为 128 位，共 2,944 行候选数据位。[逐位 TSV](payload-demand.tsv) 记录来源、位序、两端候选引脚名和 M10 矩形坐标。[端口审计](binding-audit.json) 记录各实例的逻辑收发方数量和原生端口数。

| 接收实例 | Qwen 候选输入来源数 | 当前版图的物理数据入口数 |
| --- | ---: | ---: |
| C0 | 4 | 1 |
| U0 | 3 | 1 |
| U1 | 2 | 1 |
| F0 | 2 | 1 |
| P2 | 4 | 2 |

比如 C0 的四个来源是 P2、U0、U1、F0，现有 `rx_data[127:0]` 只有一组实体落点。把四个来源直接接上会把四组输出短到一起。时分调用要有实际的选择、预约和返回通路。P/J 的两组口是 SRAM 请求/响应，接入 U/C/F 时还需要处理地址、请求、数据有效和目的写确认的传输逻辑。清单中的 2,560 位涉及候选端口分配，剩余 384 位仍属于待绑定的数据通路。主机/MEM、KV 与状态、时钟、复位和供电集成另列。#195 的单对 C/U RTL 传输和 #196 的 FFN 切片是可复用证据。

## 服务器几何结果

所有试布保留九实例位置和原生金属，M11/M12 各 2 µm 线宽和间距，via10/via11 同层边缘最小间距 2.2 µm。各组试验只布指定数据线及 P0 的 34 根本地 M→G 数据/握手线，使用真实 M10 落点。完整握手、地址和父层传输须跟随实体侧车实现。

| 组合 | 联合目标 | 结果 |
| --- | ---: | --- |
| C0↔U0 数据 + P0 M→G | 290 | `98272_1`，290/290，几何通过 |
| P0→U1 注意力 scores + P0 M→G | 162 | `98362_0/1`，两次 162/162，几何通过 |
| U1→P1 注意力概率 + P0 M→G | 162 | `98363_0/1`，两次 162/162，几何通过 |
| C0↔U0 + U1→P1 + P0 M→G | 418 | 零规则错误的最好结果 413/418；另一次 416/418 同时存在通孔间距错误 |
| Attention 两段一起 + P0 M→G | 290 | 零规则错误的最好结果 278/290 |
| 其他 4、5、9 条传输的候选 | 546、674、1186 | 零规则错误的最好结果分别 479/546、571/674、793/1186 |

逐网检查覆盖所有目标网络、连通、异网短接/间距和落点包围。五个全连通候选又通过 KLayout 0.30.12 的实际 GDS 回读、上层宽度/间距、原生 M10 包围及只增上层形状检查。各候选的检查和 GDS 摘要见 [accepted-geometry.json](accepted-geometry.json)。[run-matrix.tsv](run-matrix.tsv) 和 [slurm.txt](slurm.txt) 保留全部 54 个试布作业的结果；失败项按局部引出、主干、规则违规分别留档。

紧凑搜索初版把 8,000 DBU 误当作 8 µm，独立审计捕捉到通孔间距违规。后续按 2,000 DBU/µm 更正为 4 µm，并恢复通孔轴向相邻限制。更正前后的结果均保留，独立检查阈值一致。原有试布的默认搜索行为保留。

## 复现与原件

在独立工作目录准备 `inputs/inputs.json`、五份验收 `{P,U,C,F,J}.lef` 和 `inputs/native-gds.json`（按块类型索引实际验收 GDS）。用 [qwen_candidate.py](../../../project/experiments/nine_block_route/qwen_candidate.py) 生成清单或候选 DEF，用 [run_qwen.sh](../../../project/experiments/nine_block_route/run_qwen.sh) 调用既有搜索和独立检查。服务器使用 c64，单作业一核。

```bash
sbatch -p c64 -c 1 -J hpy-qwen-bind project/experiments/nine_block_route/run_qwen.sh audit
sbatch -p c64 -c 1 --array=0-1 -J hpy-qwen-leg project/experiments/nine_block_route/run_qwen.sh scores
sbatch -p c64 -c 1 --array=0-1 -J hpy-qwen-leg project/experiments/nine_block_route/run_qwen.sh probabilities
```

| 阶段 | 源提交 | Slurm |
| --- | --- | --- |
| r02 | `0e69c05a33b9ae2d1480896856737ecebae0dd1f` | 98271、98272 |
| r03 | `82798390030487507a3e095e19ca9da5d2423af4` | 98284 |
| r04 | `5afa8d92b3fced6cd4518dc91b760105a15628aa` | 98304–98307 |
| r05 | `0e662fe90327e2ac8e92491cec4f7535b053bf34` | 98320–98322 |
| r06 | `9b8e295d64d7f9be4fced14c542d4d15e5e1ec7f` | 98336 |
| r07 | `b47bf2763b044221cc2d87999997060d5d5587b9` | 98351–98352 |
| r08 | `5ea1de5de8cacb700f2d5e12ed94fa9a9a424067` | 98362–98363 |

原件在 `/public/home/yuzelu/PingyangHuang/issue-204-qwen-upper-route-delivery-01/qwen-204-evidence.tar.gz`。内含通过候选的实际 DEF/GDS、逐位端点、所有试布的独立检查和日志。远端与本地均核得 SHA-256 `55a527baa015414415a1a3959b00bd0309a525c00a227c982498ebfb8189217c`，163 个归档成员逐项复核，五个候选的 GDS 摘要及端点唯一性复核通过。服务器 r01 的 Windows CRLF 打包在提交前被识别，r02 使用 LF 归档。

完整产品布线仍需九实例父层传输的实体 M10 端口清单，包含选择、地址和写确认，才能对 23 个关系做同版端点分配并补齐系统线束。M10 真实落点和其余下层金属的简化模型用于后续 RC 提取。规则候选由 #199/#202 独立交付，本任务的结果为几何检查。

- 规则 rayggxia-project-collab 1.0.0，项目 `llm-hardware-design`。登记 [management-hub #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 仍待合并。仓库缺 `config/board.json`，看板未核验，待维护者同步。
