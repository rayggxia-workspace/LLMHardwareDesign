# M11/M12 2 µm OpenRCX 规则

任务 [#199](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/199)，技术与布线输入取自 [PR #194](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/194) 的 `6228d12ea20a2ae538c282697de1a92b1ca4d3af`。M10 落点为新增互联的连接边界。五份宏 LEF 作为被动联合版图的抽象。模型的场解以明确的导体样例代表下方金属环境。

**候选规则已生成，整版耦合验收未通过。** [规则文件](candidate/research12.rules)用于复现实验和定位 OpenRCX 的跨层漏项。当前资格由[服务器回执](../../../work/huangpingyang04-lgtm/199/README.md)界定。

## 服务器结果

- Slurm `98197` 在 c64 的 48 核上生成 4,656 组样例，拟合使用 9,496 行三维场解和 1,364 个线阻样例。2,472 张规则表中 2,284 张非空，188 张为空是 OpenRCX 不查询的格式槽位。必需表均有数据，拟合前的 SPEF 逐网读回误差指标均小于 `6e-8`（分母为 `max(1, |参考值|)`）。
- 所有 14 个留出目标的线阻相对误差约 0.67%。M11/M12 的 2 µm 同层间距样例通过逐项门槛。3/4 µm 样例的总电容量级接近场解，但部分线对的耦合误差超过门槛。例如 4 µm 间距时，M11 一侧最近邻由场解得到约 11.94 fF，OpenRCX 给出 13.63 fF，另外的显著线对仍存在较大的误差。
- OpenRCX 1.0、2.0、2.2、2.3 均遗漏了留出样例中的跨层正交耦合。例如 M11 中心线与五条 M12 交叉线的参考耦合之和为 **3.664 fF**，四个提取模式都输出 **0 fF**。跨层平行样例也有漏项。留出阈值沿用已有流程，运行后未放宽。
- Slurm `98237` 用与 #194 归档 SHA-256 一致的技术 LEF、DEF 和五份宏 LEF 导出 296/296 根网的诊断 SPEF。逐网 SPEF 电阻图均连通两个端点，两个通孔样例均独立读回 **0.08 Ω**。首轮通孔总线阻误差来自默认线端延伸，通过显式零延伸对照核验。网数和电阻连通的通过项与跨层电容资格分别记录。

## 输入与方法

- 上层宽度和厚度均为 2 µm，最小间距 2 µm，层间介质厚 0.8 µm。M10、M11、M12 底面分别为 10.09、12.89、15.69 µm。使用均匀相对介电常数 3.9、上层方块电阻 0.03 Ω/□ 和两种通孔各 0.08 Ω 的研究假设。完整输入见 [2 µm 配置](../block_v1/technology-2um-v1.json)。
- OpenRCX 按宽度倍率 1/2、间距倍率 1/2/4/8 生成样例。原生层样例用于覆盖规则格式中的上下文，M11/M12 的数据按 2 µm 叠层重新求解。逐个场景保存实际 DEF 几何及 3D FSV Maxwell 行。SPEF 读回核对线阻、对地 C、耦合 C，再调用 `gen_rcx_model` 生成规则。
- 独立样例使用 150 倍线宽的线段，覆盖 M11/M12 同层 2/3/4 µm 间距、M10/M11 与 M11/M12 跨层平行及正交。两种通孔另用实接 DEF 和解析线阻检查。对照用 [#194](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/194) 的联合 `escape-97881-30/escape-2.def` 及五份 LEF，按归档 SHA-256 读回。

## 复现

把本实验目录及同版 `project/experiments/block_v1/` 依赖复制到授权的新任务目录。下列命令从该目录运行。输入容器和场求解器 SHA-256 在脚本中固定。场解脚本沿用 [#121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121) 先前核验的独立 FSV 二进制，源码和构建入口见 [fsv_build.py](../block_v1/fsv_build.py)。

```bash
sbatch -p c64 -N 1 -c 48 --output=slurm-%j.log \
  project/experiments/m11_m12_rcx/run.sbatch

# 在独立输出目录中比较不同 OpenRCX 提取引擎，重用同一版规则。
sbatch -p c64 -N 1 -c 8 --output=slurm-%j.log \
  project/experiments/m11_m12_rcx/run.sbatch --reuse-fit /path/to/job-ID --version 2.3

# 核对 via10/via11 和 #194 联合试布读回。
sbatch -p c64 -N 1 -c 2 --output=slurm-%j.log \
  project/experiments/m11_m12_rcx/coupon.sbatch --fit /path/to/job-ID \
  --archive /path/to/nine-block-coupons.tar.gz --lef-dir /path/to/approved-LEFs
```

主要输出为 `fit/research12.rules`、拟合与 SPEF 读回记录、`heldout/heldout-rc.json` 及留出样例 SPEF。独立样例不通过时命令返回非零，拟合产物和失败证据仍保留。使用时以逐项留出结果限定适用范围。
