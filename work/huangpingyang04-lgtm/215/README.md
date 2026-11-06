# #206 九宏 M11/M12 顶层寄生提取

[Issue #215](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/215) · [布线 PR #206](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/206) · [提取方法 PR #202](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/202)

使用 #206 提交 `179ca76ff35673dcb47986e3d873fc2a87dbabbb` 的[最终布线回执](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/179ca76ff35673dcb47986e3d873fc2a87dbabbb/work/huangpingyang04-lgtm/204/nine-upper-routed.json)，以及 #202 提交 `20b945d3cdb73d74778bdccc4952eb4315170cd8` 已通过 14 个原样例的场求解器。以 #206 实际 ODB 和逐网矩形为准。范围包括九个计算宏到传输宏的 2,491 根信号，提取从 M10 落点经 via10、M11、via11、M12 到对端 M10 落点。

## 方法与服务器结果

1. **作业 99157，输入与电阻图。** 核对 ODB、DEF、GDS、LEF 及既有独立几何回执。OpenRCX 提取后，按每个网的两个原端点及逐段电阻，将原 SPEF 节点逐一绑定到实际几何。2,491 根网的导体盒与 OpenDB 导出矩形逐网集合相等，共 32,828 个导体盒、18,905 个电阻节点和 16,414 条电阻边。[输入与绑定回执](geometry.json)
2. **作业 99161，整版场求解。** 16 个 Slurm 分片仅拆分激励网，每行均读取相同的完整导体场景。完成 2,491 行 Maxwell 电容和节点分箱，共 10,171,595,776 次随机游走。逐网总电容的最大统计标准误差为 0.241%。[Slurm 终态](slurm.txt)
3. **作业 99183，SPEF 组装。** 按 #202 门槛校验互易和电荷守恒，按左网分块合并双向节点电容，逐字节保留原 SPEF 的端点和电阻记录。对角最大变化 0.530%。组装出 586,172 个非零互容网对、8,234,564 个节点对电容。实际几何投影相交的 18,329 个 M11/M12 网对均有非零互容。[组装回执](assembly.json)
4. **作业 99186，OpenDB 独立读回。** 以 #206 原始 ODB 加载新 SPEF。逐一核对 2,491 网、4,982 个端点、16,414 条电阻边及全部网对互容。互容读回的最大缩放误差为 `5.80e-8`，分母为 `max(1 fF, 参考互容)`。18,329 个投影相交网对全部读回非零。OpenDB 提示输入无顶层 `*PORTS`，本次 4,982 个端点均是实例引脚。[读回回执](readback.json)

最高端到端线阻为 `word_1960` 的 **65.24 Ω**。逐网 (C_g+C_c) 最大为 `word_1974` 的 **445.89 fF**，其中对地 80.30 fF，耦合合计 365.59 fF。原始无表头 TSV 列依次为网名、电阻 Ω、对地电容 fF、耦合总和 fF、实例端点数、由本网作为源记录的节点对数。[逐网 RC](net-rc.tsv) · [证据摘要](SHA256SUMS)

## 完整 SPEF

- 路径 `/public/home/yuzelu/PingyangHuang/issue-215-top-pex-paPJkRpL/job-99183/result/field.spef`
- 文件大小 353,865,339 字节
- SHA-256 `27438d3106403200343f17fd4984385f81f84c4e3a748324883c55c93b05618c`

原始矩阵分片、组装和读回日志保留在以下实际提交目录。各目录的输入包 SHA-256 在提交前与服务器核验。

| 阶段 | 服务器目录名 | 输入包 SHA-256 |
| --- | --- | --- |
| 几何与电阻 | `issue-215-top-pex-zOz2uxIr` | `46406277c44cea7b678f15ed8fa9d8e5025d8374fee0c3c6279887376547e2b7` |
| 场解分片 | `issue-215-top-pex-mKnz4Tv5` | `cf7ccb2a2c2158fe3e93a3212f10758fcba112e379a18efa30639f9dcd6f5186` |
| SPEF 组装 | `issue-215-top-pex-paPJkRpL` | `ab196cbbf3d122102a9d6e400cdef31ad13a44e0a8003595548787c0eb94f8a4` |
| OpenDB 读回 | `issue-215-top-pex-ZU0ApzLR` | `cb9ef038d561c754be8f5d4918cfec4ec243f1003d4ddd5e5da9362db82d1bbf` |

## 验收边界

电容沿用 #202 的均匀介质、参考地平面和 M10 落点抽象。父层未接入的 44 个控制、时钟和复位端点沿用 #206 的独立边界。节点电容按物理电阻节点分箱，网级和网对级经验证，节点局部分布的独立收敛仍待实版对照。300 MHz 系统 STA 属于后续验收。

## 复现

在自己的新服务器工作目录上传同版脚本，将 #206 固定提交里的 `work/huangpingyang04-lgtm/204/nine-upper-routed.json` 原字节保存为 `route-206.json`。下列命令的阶段产物按实际作业号传给下一步。

```bash
root=/public/home/yuzelu/PingyangHuang
accepted="$root/issue-199-field-xXrAwSOn/job-98267"
rules="$root/issue-199-rcx-w4JD5wxq/job-98197/fit/research12.rules"
job=project/experiments/m11_m12_rcx/top_pex.sbatch
sbatch -p c64 -N 1 -c 4 --output=slurm-%j.log "$job" prepare \
  --receipt "$PWD/route-206.json" --rules "$rules" --accepted "$accepted"
sbatch -p c96 -N 1 -c 24 --array=0-15%16 --output=slurm-%A_%a.log "$job" solve \
  --prep /path/to/prepare/job-ID/result --accepted "$accepted" --shards 16
sbatch -p c64 -N 1 -c 4 --output=slurm-%j.log "$job" assemble \
  --prep /path/to/prepare/job-ID/result --rows-dir /path/to/array-submit-directory
sbatch -p c64 -N 1 -c 4 --output=slurm-%j.log "$job" readback \
  --prep /path/to/prepare/job-ID/result --assembly /path/to/assemble/job-ID/result \
  --receipt "$PWD/route-206.json"
```

执行身份 `huangpingyang04-lgtm`，项目 `llm-hardware-design`。遵循 `rayggxia-project-collab 1.0.0`。登记 [management-hub #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 待合并。仓库无 `config/board.json`，看板状态待维护者核验，独立审查人待指定。
