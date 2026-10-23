# 完整硬件集成实验（Issue #55）

本入口承接两个完整原始硬件顶层：openTPU `otpu_asic_top` 的 small 配置，以及 `llaccel_core`（EPILOGUE_FUSION=0）。采用资源并集；现有 ACT/MXU/GEMM/VECTOR 保留为核心输入，未划分的控制、存储与接口逻辑另做案例辅助分区。不是最终团队 Block 规格，也不是 LLM 图编译器。

阶段一清单/基准验收为pass_with_inherited_issues；原完整 RTL 有有限回归通过，完整分块替换、共同冻结底座和最终定制布线尚未通过。[阶段记录](../../../docs/experiments/issue-55-full-block-integration.md)与[算法说明](../../../docs/experiments/issue-55-block-integration-methods.md)给出实际证据边界。

本轮主路线：M1–M8 固定，M9/M10 及真实 M8↔M9、M9↔M10 通孔定制；M11/M12 只保留为单独后备评估。原始 Block 中已有高层占用，必须先在派生副本真实迁线，不能删除或隐藏几何。

## 环境与运行约定

- 唯一服务器根目录：`/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z`。
- 当前源码：该目录下 `worktree/project/experiments/block_full_integration/`；运行使用每个 driver 目录中的 Git commit 快照。
- Slurm c64/c96，作业名 `hpy-*`。当前检查/资格任务每个 1 CPU；进程内存限制与缓存位置见实际 `run.sbatch`。
- 既有 ORFS Singularity 容器：`/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif`；执行 `source /OpenROAD-flow-scripts/env.sh` 后使用现有 OpenROAD/Yosys。
- 原始输入只读。每次新实验须新 `driver` 和输出路径。失败目录也不覆盖。
- 仿真涉及既有 Verilator/Intel 编译器及 FakeRAM 行为模型；模型不代表真实 SRAM 工艺资格。

## 实际入口和范围

| 入口/适配器 | 已执行能力 | 未完成部分 |
| --- | --- | --- |
| `flow.py inventory --adapter native` / `native_inventory.py` | 完整 ODB 实例、pin、wire/via、PG、技术层表；四宏实际完成 | 不等于 DRC/连通/STA |
| `flow.py inventory --adapter rtl` / `rtl_inventory.py` | 锁定原构建、选用源码、21项归属前沿和历史基准 | 归属前沿与完整展开证据结合使用 |
| `flow.py integrate` / `partition.py` | 两个真实完整顶层展开、状态/内存归属 | 分区变换及集成功能对照尚未通过 |
| `flow.py verify --adapter native` | 完整原生表独立一致性核对 | 不能代替真实几何连通 |
| `native_geometry.py` | 指定目标网端点连通，目标对全部邻近导体/PG/引脚短接检查；ACT原69网通过 | 不检查无关非目标网之间的短路，不代替全部工艺DRC |
| `migrate.py` | 原生 FIXED 路线导入资格；支持复用已关闭准备/路由证据 | 迁线、提取和时序按各次真实收据验收 |
| `baseline_replay.py` | 原完整 llaccel seed0/2 补测 | 不是新集成 DUT |
| `compile_open_observer.py`、`replay_open_observer.py` | 原完整open小配置观察器构建及20例回放 | 集成DUT逐周期对照尚未运行 |
| `flow.py replay` | 验证原生库存输入/代码/工具SHA后在新目录重放 | 目前仅原生库存类型 |
| `flow.py prepare-base`、`flow.py route` | 未实现时明确非零退出 | 共同底座与最终定制路由适配器仍待实现 |

## 已实际执行的命令

以下为作业内真实调用的命令形式，`SOURCE` 指对应 driver 保存的源码快照。历史输出目录不可重复写入。

```bash
python3 -B -I -S "$SOURCE/project/experiments/block_full_integration/partition.py" elaborate --case llaccel --task-root "$ROOT" --out "$ROOT/runs/hierarchy-llaccel-03" --seconds 1200 --max-as-gib 24
python3 -B -I -S "$SOURCE/project/experiments/block_full_integration/replay_open_observer.py" --run-root "$ROOT/runs/open-observer-replay-01"
python3 -B -I -S "$SOURCE/project/experiments/block_full_integration/native_geometry.py" --input "$ROOT/runs/native-act-01/native" --manifest "$ROOT/runs/native-act-01/execution.json" --targets "$ROOT/runs/migration-prepare-act-02/targets.json" --output "$ROOT/runs/native-geometry-act-01-driver/original-target-geometry.json"
```

各命令完整环境与选项以 `runs/<driver>/run.sbatch` 为准；对应作业89958、89965、89966。提交器 `submit.py --spec <JSON>` 将指定 Git commit 归档到新 driver 后提交，不使用会变化的工作区源码。

复跑时复制所需小型 driver 配置到本任务新 `configs/` 文件，修改 `driver`、`source_commit` 和输出路径，再调用提交器；输入、层范围或工具改变后，旧通过结果不自动沿用。准备/路由恢复入口还检查相关数据库、原生表和比较报告的 SHA。

配置分为：`native_candidates.json`（实际宏和工艺输入）、`partition_cases.json`（原顶层/文件表/核心边界）、`baseline_extra.json`、`open_observer_*.json`（有限测试与参考结果）。其中案例选择和服务器路径属于适配输入；正式 Block 接入须替换能力、尺寸、实际 pin/障碍/时序模型和目标连接，不能仅改名字。

大型数据库、trace、全部日志保留在服务器。仓库 `results/summary.json` 与少量CSV仅提供索引，不重新包装原工艺或设计源码。
