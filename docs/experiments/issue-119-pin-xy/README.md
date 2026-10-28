# Issue #119 图表与数据

[中文结论及两块对照图](../issue-119-pin-xy-candidates.md) · [详细 HTML](report.html) · [脚本说明](../../../project/experiments/pin_xy_candidates/README.md)

`assets/` 收录 ACT/GEMM 的 comparison、zoom、endpoints 六张图，每张同时提供 PNG 和 SVG。comparison 为同边界/同坐标尺度的 A/B/C 三联图；zoom 独立取窗，端点图虚线仅为 L1 示意。标记放大不代表通孔尺寸。

`data/*csv.gz` 均为逐字节压缩的 UTF-8 BOM CSV，解压后可用 Excel 或 pandas 读取：

```python
import pandas as pd
pins = pd.read_csv('data/all_pin_coordinates.csv.gz')
print(pins.query("case == 'act' and plan == 'C' and layer == 'metal6'"))
```

- `all_pin_coordinates.csv.gz`：13,839 行，主键 `(case, plan, pin)`；另有逐块文件。
- `*_groups.csv.gz`：每方案的逐 pin 分束和语义依据；B 原边近邻、C 连续位号，实际字节对单列。
- `*_pg_coordinates.csv.gz`：独立 PG 访问矩形，不计入信号位数。
- `source_pin_data.json.gz`、`*.meta.json`：原报告内嵌快照，用于本地重核坐标。
- `metrics.json`、`proposed_patches.json`：几何指标、风险数量和候选束区域。
- `validation.json`、`package_validation.json`、`html_qa.json`：原分析阶段检查回执；其中完整交互 HTML 的回执针对原离线版，并非当前去掉悬停的仓库摘要版。
- `tool_receipt.json`、`extraction_receipt.json`、`source-index.json`、`manifest.json`：原输入/工具 SHA、只读远程路径及本次入库字节索引。原回执中的“未提交 GitHub”是首次交付时的历史状态，本次发布以 Issue/PR 为准。

仓库 HTML 采用相对路径图片，下载整目录后打开；GitHub 直接预览请读 Markdown 摘要。完整原始金属/单元表约 20 MiB，仅留远程授权目录，不重复入库。本地完整交互交付包的 SHA/大小在 source-index 中，重画流程见脚本说明。

只运行仓库校验，无需服务器或绘图依赖：

```sh
python project/experiments/pin_xy_candidates/validate_repository.py
```

完整物理接入、详细布线、RC、时序与 DRC 未执行，不将清单验证当作签核通过。
