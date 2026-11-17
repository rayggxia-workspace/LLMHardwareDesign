# 九底座原生接口布线证据

[结果与验收边界](../../../../../docs/experiments/pr271-nine-native-data-links.md) · [Issue #250](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/250) · [PR #285](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/285)。当前九块版本替代旧 14 实例版本；旧文件保留作历史记录。

- `final/layout.png`、`final/271-nine-native-four-links.oas`：九底座总图与实际 M11/M12 路由。
- `final/connections.csv`：1,053 个分支，完整端点名称和组别；`spec.json.gz` / `route.json.gz` / `checks.json`：1,049 网的可复核几何。
- `final/native-*`：原生 M7–M10 几何与端口表。C/P2 的 `native.drc` 空文件表示指定接口局部 DRT 零违规，范围分别为 512 / 206 网；不是全芯片零 DRC。
- `release-support/native-rtl`、`native-interface.patch.gz`：本实验 C0/P2 接口变体、八个修改文件及定向测试依赖，不直接替换生产 RTL。
- `release-support/logs`：无损压缩的原生层次 lint、定向 RTL、局部 DRT、网表合并日志，也保留 P2 全接口 DRT 的失败记录。
- `physical-scripts`：最终运行的 C 512 网 / P2 Down 206 网详细布线和合并脚本；`reproduction` 保留准备、布局、布线及导出步骤。物理脚本中的绝对路径指向获授权的服务器实验输入，不保证脱离服务器即可重建完整物理实现。
- `provenance.json`：输入代码版本、服务器位置、作业编号与文件哈希；`final/native-provenance.json` 固定最终 ODB 指纹。OpenROAD 日志未报告可识别版本，KLayout 版本未记录，均不补写推测值。

在仓库根目录运行：

```bash
python -B work/huangpingyang04-lgtm/250/pr271-data-link-routing/nine-native/verify_nine.py
bash work/huangpingyang04-lgtm/250/pr271-data-link-routing/nine-native/run_tests.sh /absolute/new-output-directory
```

第一条只需 Python 标准库。第二条需 Linux、C++ 构建环境和 Verilator（本次 5.042），可通过 `VERILATOR` 指定可执行文件；集群运行须在 Slurm 计算节点。绘图使用 `plot_nine.py` 和 matplotlib。`lower-overlay.json.gz` 是无损压缩的历史低层引出几何，校验器自动解压读取。

OASIS 是真实上层信号覆盖层与原生 M7–M10 接口/抽象几何的合版视图。九块身份和全部顶层连通已验证；P2 既有 S 内部网、整机生命周期与累加数值、完整制造 DRC/LVS/PG/RC/STA 仍在报告列出的待验收范围内。
