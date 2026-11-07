# M11/M12 2 µm OpenRCX 规则

任务 [#199](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/199)，技术与布线输入取自 [PR #194](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/194) 的 `6228d12ea20a2ae538c282697de1a92b1ca4d3af`。M10 落点为新增互联的连接边界。五份宏 LEF 作为被动联合版图的抽象。模型的场解以明确的导体样例代表下方金属环境。

[九宏顶层 RC 提取](../../../work/huangpingyang04-lgtm/215/README.md)将此方法用于 #206 的实际 2,491 网版图，保留同一 2 µm 叠层和 M10 落点边界。

[#217 铜参数版本](copper/README.md)在固定布线和尺寸下重新提取 R，复用同一静电 C，分别记录主版本、电阻率敏感性和理想通孔下限。原研究基线并非标定的铝工艺。

**场解提取路径已通过原留出门槛，随后完成 #194 的 296 网整版提取。** 原 [OpenRCX 规则文件](candidate/research12.rules)保留作对照。下文先给修复方法和新版 SPEF，再保留原查表候选的拟合结果。

## 跨层漏项和修复

OpenRCX 的上下层覆盖计算把垂直方向的重叠交给覆盖长度查表。v2 的 `GetCrossOvelaps` 为重叠片保留位置和长度，目标导体指针为空，后续覆盖分支可以修正电容上下文，但该重叠片没有可用于输出两网互容的对端。v1 的 `computeOverOrUnderSeq` 同样以覆盖长度调用 OVER/UNDER 规则，显式互容由单独的相邻线搜索提供。原留出中跨层平行有非零项，跨层正交四种模式均为零，符合该路径。调节规则表系数无法恢复此处缺失的对端身份。[v1 覆盖计算](https://github.com/The-OpenROAD-Project/OpenROAD/blob/2eba27b2c602b3b1a8f0fdc7773a5387d58fddaa/src/rcx/src/extmeasure.cpp#L806-L859) · [v2 正交重叠](https://github.com/The-OpenROAD-Project/OpenROAD/blob/2eba27b2c602b3b1a8f0fdc7773a5387d58fddaa/src/rcx/src/extmeasure_couple.cpp#L1172-L1206)

修复保留 OpenRCX 的端口和电阻边，电容由 3D FSV 从全部导体共同求解。起点和终点通量按物理电阻节点分箱。对两个激励方向取平均，将正的互容分箱归一至该网对的测量值，保留逐网守恒核验。随后重写 SPEF 电容段，并用 OpenDB 逐网和逐网对读回核对。原留出参考沿用同一个场求解器的冻结结果，新运行使用不同随机种子和高斯面偏置，并验证实际 SPEF 的写入与读回。

| 顺序 | 已执行结果 |
| --- | --- |
| Slurm 98267，原留出样例 | 原 10 组几何、14 个目标，全部通过原门槛。总 C 最大相对误差 0.304%。典型 M11/M12 正交目标的跨层 Cc 之和从查表的 0 fF 恢复为 **3.650 fF**，原参考 3.664 fF。 |
| Slurm 98299，#194 联合试布 | 296 根网、8,508 个导体盒与 4,402 个电阻节点一起求解。保留全部 4,106 条原电阻边。几何投影相交的 **11,743/11,743 个 M11/M12 网对**均有非零互容。OpenDB 读回 36,796 个耦合网对及 2,210,762 个节点对电容。 |

整版 SPEF 为 `/public/home/yuzelu/PingyangHuang/issue-199-field-FIt2gk4X/job-98299/field.spef`，SHA-256 为 `660d63e531b75c858b669cf32da7c458b0f2951648f1443e7a5ff13803b37b6a`。[场解回执与复现命令](../../../work/huangpingyang04-lgtm/199/field-repair/README.md)

本结果覆盖 #194 的被动试布。M10 按落点方块建模，边界下方采用均匀介质和地平面，宏内部保持黑盒。两个 ready 代理端点、实际父层供电与时钟的边界随原试布。原留出门槛验证逐网和逐网对电容，节点局部分布的独立收敛及系统时序留待实版验证。

## 原查表候选的服务器结果

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
