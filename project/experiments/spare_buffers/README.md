# 预制底座备用 buffer 与 M10 引出

脚本在 Nangate45 / FreePDK45 底座的块间空隙预布备用 `BUF_X32`。每颗的输入 A 和输出 Z 各引到一块 2 × 2 µm 的 M10 端口，供后续上层连接。样板组内的 VDD/VSS 接到本组 M10 电源条。

## 新底座

在项目现有的 ORFS/Nangate45 容器内运行，需要 Bash、Python 3、OpenROAD 与支持 Python 宏的 KLayout。复制 [base-manifest.example.json](base-manifest.example.json)，改为新底座的数据。

- `base_stream` 指向 GDS 或 OASIS，可使用相对于清单的路径。只含一个顶层时可省略 `top_cell`。
- `bounds_dbu` 是芯片边界，`boxes_dbu` 是各 block 的包络。坐标与原版图使用同一原点，统一按每微米 2,000 DBU 填写，矩形顺序为左、下、右、上。版图数据库精度须能无损转换到 0.0001 µm 的输出网格。
- `keepouts_dbu` 可选，用来预留尚未画进版图的走线通道、电源区或其他禁放区。脚本还检查原版图内 GDS 1–29 层的已有几何，包括原走线和过孔。

```bash
bash project/experiments/spare_buffers/run.sh my-base.json new-spare-run
```

可选的第 3 个参数限制样板组数，默认 `0` 表示填充全部合规网格位。第 4 个参数设置 X/Y 步长（默认 `56,64` µm）。每组有 4 颗 buffer。试验时可先给小的组数，脚本会在候选位置中分散采样。

脚本用 OpenROAD 选 M10 端口、布线并验证样板。KLayout 扫描块间空隙，排除 block、留空区和已有几何，在新文件中合入样板。输出位于 `new-spare-run/merged/`。

| 文件 | 用途 |
| --- | --- |
| `base-with-spares.oas` | 原底座与新增样板的合版 |
| `spare-overlay.oas` | 仅新增 buffer、走线和端口的版图 |
| `m10-ports.tsv` | A、Z 和局部 PG 端口的中心及边界，单位 µm |
| `banks.tsv`、`summary.json` | 样板位置、数量、原底座来源和校验摘要 |
| `stream-verification.json`、`overlay.lyrdb`、`outputs.sha256` | 合版回读、新增版图 DRC 与文件校验 |

适用范围为块间空隙。当前样板使用 Nangate45 `BUF_X32`，并沿用 PR271 的 0.2 µm 接入网格，原点为 (0.095, 0.070) µm。固定样板按组填充，每组与 block 至少保留 2 µm。整底座的电源连接、备用输入的上电状态、后续上层布线和整底座 DRC/LVS 需要在整合时验证。

## 复跑和回归

```bash
# 隔离的小型新底座，验证原 M10 走线避让和原铜回读
bash project/experiments/spare_buffers/smoke_test.sh new-smoke-run

# PR271 方案 A 的 112878 布局 JSON 和归档分块视图清单
bash project/experiments/spare_buffers/run.sh --pr271 placement.json /path/to/overlay-111993/base.json new-pr271-run
```

PR271 归档模式使用已有 GDS 或由 ODB 导出的块版图重建试摆。U0 仍使用 Gather 暂存视图。PR271 原实跑为 Slurm 118486 / 118489，1,772 组、7,088 颗 buffer 和 14,176 个 M10 信号端口，新增版图 DRC 为零。归档 OASIS 和大体积输入保留在项目授权存储。
