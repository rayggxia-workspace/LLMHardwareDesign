# 六种基础宏交付；R 尚未完成

> 2026-11-02 用户纠正：撤销助手此前写入的 R 禁止发射、禁用、不调度，以及失败后不再修复或重跑等额外限制；这些不是用户要求。R 纳入正常的计算宏实现、控制适配、互联接入及调度验证。已有失败和未完成状态继续如实记录，验收标准不变。

2026-11-01，按用户决定，先交付 M/N/E/G/S/T，不等待 R。任务 [#143](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/143)，研究过程保存在 [PR #144](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/144)。

| 宏 | 最终选择 | 边长 µm | active 面积 µm² | setup ns | hold ns | 状态 |
|---|---|---:|---:|---:|---:|---|
| M | M | 930 | 304530.898 | +0.039857 | +0.018500 | 合格且本地实收 |
| N | N-q14 | 510 | 68015.668 | +0.140712 | +0.017753 | 合格且本地实收 |
| E | E-wide，含 op13 | 600 | 63751.688 | +0.412125 | +0.019608 | 合格且本地实收 |
| G | G-v2 | 400 | 22831.046 | +0.512034 | +0.017721 | 合格且本地实收 |
| S | 16 KiB，含供数器 | 1680 | 1181315.842 | +0.028545 | +0.007200 | 合格且本地实收 |
| T | 6 KiB 结果交接 | 1040 | 431244.786 | +0.429092 | +0.007988 | 合格且本地实收 |
| R | 原 S32 状态 RTL，仅供后续研究 | — | — | — | — | **未完成，未选入合格清单** |

共同合同：Nangate45 typical、300 MHz、时钟不确定度 0.1 ns、BUFX2 输入驱动、50 fF 输出负载、IO 最大/最小延迟 0.8/0.2 ns。M1–M10 固定，M10 接点在宏内。S/T 使用标准单元存储，不是 SRAM 宏。功能、格式、接口及周期详见 [实施合同](BLOCK_V2.md)。

六种合格叶子的证据包括：最终六文件 V/SDC/DEF/ODB/SPEF/GDS、fresh RC 和全端点时序/电气、PG/连通、原生完整 DRC、未删规则 GDS deck、三初态最终物理网表功能、严格等价、真实几何及 M10 接点。证据和文件逐 SHA 绑定，旧候选资格不会自动转移给新 RTL。

最终索引：[release-six/index.json](../work/YUZE-LU/143/release-six/index.json)。其中记录每块准确的 RTL SHA、远程归档位置、最终文件 SHA、本地实收回执，以及不超过64KiB的轻量原始资格文件；较大原始报告保存在原归档，完整成员清单及SHA仍在每块bundle.json中。大文件不进入 Git；本地路径为 `D:\Data\LLMHardwareDesign-issue143-runtime\deliverables\` 下的 M、N-q14、E-wide、G-v2、S、T。共 249 个已解包成员重新核验。S 的归档包没有下载，但全部 27 个成员已独立下载核验，索引保留这个区别。

## 使用和核验

```powershell
python -X utf8 scripts/check_project.py
python -X utf8 project/experiments/block_v2/check_release.py
# 仅在具有索引所列本地物理数据的机器上执行：
python -X utf8 project/experiments/block_v2/check_release.py --local-artifacts
```

仓库内检查只证明交付内容与原验收证据一致，不是重新运行 EDA。既有物理结果的工具、命令、输入与输出 SHA 保留在各宏原始回执内；Linux/Slurm/固定 ORFS 环境运行代码见 `project/experiments/block_v2` 及其 `block_v1`、`block_feed_v1` 依赖。运行器不因导入而提交作业，重新执行必须使用新的独立输出目录，并遵守 [服务器规则](REMOTE_RULES.md)。本次整合不重跑已验收物理流程。

## R 的边界和后续

R 仅保留 `project/rtl/block_library_v1/block_v1_r.sv` 作为未完成研究源码。交付时仍缺完整原生 DRC 的最终判定、最终资格汇合和本地完整实收；已经通过的单项不能代替这些缺项。原作业和失败证据保留，不作为六块交付的依赖；R 的后续候选、修复和重跑可正常推进，仍须满足全部适用验收。后续若真正取得完整资格，应以新证据另行更新，不自动改变本索引。

本交付只声明六个典型角叶子，不包含层级 Liberty、M11/M12 系统、阵列或整模型整数质量及系统吞吐验收。
