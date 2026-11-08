# 跨层耦合修复的服务器回执

[Issue #199](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/199) · [PR #202](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/202) · [#194 输入](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/194) · [方法和结果](../../../../project/experiments/m11_m12_rcx/README.md)

## 服务器结果

- `98267` 在 c96 的 node18 使用 48 核，19 秒，退出 `0:0`。冻结 [原留出几何和门槛](../heldout-v1.0.json)，以新随机种子重求解全部 70 根线，并对原 14 个目标做独立于拟合的验收。读回检查含 R、总 C、Cg、Cc 总和、显著线对和跨层线对非零。三维场求解器文件的 SHA-256 为 `d6fb74c21b2a40bd08b4f4d7c798f147b29ed4f6732b919b137f6a527ee0333a`。[逐目标回执](heldout-validation.json)
- `98299` 在 c96 的 node19 使用 64 核，1 分 48 秒，退出 `0:0`。先读取并核验已通过的 `98267` 回执与同一求解器，再用 #194 原始归档建立 296 网共同电场。导体图与原 SPEF 的端点和逐段电阻逐一绑定。296/296 网完成 SPEF 导出和读回，全部 11,743 个跨层投影相交网对有非零互容。场解逐网总电容的最大统计标准误差为 0.242%，互易平均及非负化后的最大行对角改变量为 0.398%。[几何回执](coupon-geometry.json) · [整版回执](coupon-validation.json)
- 整版 SPEF 共 87,259,986 字节。原文件及 OpenDB 逐网对回执保留在服务器的授权任务目录。读回日志中的六个宏实例缺失提示对应 #194 试布中无信号网接入的实例，296 个目标网均在读回清单内。[作业终态](slurm.txt)

## 输入和产物

| 用途 | 路径或 SHA-256 |
| --- | --- |
| #194 联合归档 | `f4b5b8974121f2607592ed99a567c3d4b44b51191c989c6f45016f67ea0884d8` |
| 留出任务输入包 | `e01f74ab92e3ac7753340eebfa2b90c6058cbecc448cadf8af5df50727c9295d` |
| 整版任务输入包 | `f7e3db07553842bb7d951aea5aa00d8bd728d8947d79165b22f478f4da262e40` |
| 留出 SPEF | `/public/home/yuzelu/PingyangHuang/issue-199-field-xXrAwSOn/job-98267/result/field.spef` |
| 整版 SPEF | `/public/home/yuzelu/PingyangHuang/issue-199-field-FIt2gk4X/job-98299/field.spef` |
| 整版 SPEF SHA-256 | `660d63e531b75c858b669cf32da7c458b0f2951648f1443e7a5ff13803b37b6a` |

轻量证据逐字节核对见 [SHA256SUMS](SHA256SUMS)，编译使用 #121 已核验的 FSV 对象及固定研究容器。[求解器链接输入](solver-inputs.sha256)

## 复现

在自己的新服务器任务目录保留同版 `project/experiments/m11_m12_rcx` 和 `project/experiments/block_v1` 脚本。下列路径为本次已经核验的实际输入。整版入口强制读回固定留出回执和求解器 SHA，留出通过后才提交。

```bash
root=/public/home/yuzelu/PingyangHuang
fit="$root/issue-199-rcx-w4JD5wxq/job-98197"
approved="$root/issue-199-field-xXrAwSOn/job-98267"
base="$root/issue-199-rcx-8BUE7MyE/job-98237/coupon"
archive=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-191-nine-block-route/release-coupon-01/nine-block-coupons.tar.gz

sbatch -p c96 -N 1 -c 48 --output=slurm-%j.log \
  project/experiments/m11_m12_rcx/field.sbatch --fit "$fit"

sbatch -p c96 -N 1 -c 64 --output=slurm-%j.log \
  project/experiments/m11_m12_rcx/field.sbatch --coupon \
  --fit "$fit" --approved "$approved" --base "$base" --archive "$archive"
```
