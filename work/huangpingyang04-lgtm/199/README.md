# #199 服务器回执

任务 [#199](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/199)，执行账号 `huangpingyang04-lgtm`。规则 `rayggxia-project-collab 1.0.0`，项目 `llm-hardware-design`。登记 [management-hub #5](https://github.com/rayggxia-workspace/management-hub/pull/5) pending。仓库缺 `config/board.json`，实际看板 unverified，同步待管理员核验。独立审查人待指定。

## 输入和原件

- [#194 固定版本](https://github.com/rayggxia-workspace/LLMHardwareDesign/tree/6228d12ea20a2ae538c282697de1a92b1ca4d3af) 的配置 Git blob 为 `a9620d271235806ba6039a83d5d265dbb01b88cb`，`overlay.py` 为 `ea2041af2775f922b2ddf2bdeb6ed4c5dd673870`。生成技术 LEF 的 SHA-256 为 `7900c84841227beefe10c3dee846399470526b21edc81eb1953b4f920d4bb90a`，与 #194 归档记录一致。
- Slurm `98197` 的输入包 SHA-256 为 `31eed0b227241bfd76159958f81761da7e0db9c8016494cb75b32115245efc9a`。运行根目录为 `/public/home/yuzelu/PingyangHuang/issue-199-rcx-w4JD5wxq`。保存了场景、各分片原始 Maxwell 行、生成命令、完整参考 SPEF、规则和留出比较。
- Slurm `98219`、`98220–98222` 的输入包 SHA-256 为 `27e22a9860441fc5be92029e5dfe0020dc41404a25b291f2483e159b0ce58d6b`。运行根目录为 `/public/home/yuzelu/PingyangHuang/issue-199-rcx-OZWlFL4w`。
- Slurm `98237` 的输入包 SHA-256 为 `aebff359fdae19a5104cac7d6e6c1544eb3bde7f3fb6a234a4ef4359fa871878`。运行根目录为 `/public/home/yuzelu/PingyangHuang/issue-199-rcx-8BUE7MyE`。原件含 `job-98237/coupon/extracted.spef` 及两种端部延伸对照。
- 仓库副本与服务器原件逐一校验，摘要见 [SHA256SUMS](SHA256SUMS)。规则 SHA-256 为 `aecdef8095035174326193c7dbb2ca4868c2a3acc3bc224bc89a2bb9b58101d2`。原件按授权目录留存。

## 结果索引

| 作业 | 回执 |
| --- | --- |
| 98195、98196 | 启动失败，分别定位为计算节点的 Singularity 路径和镜像内的 Python 3.10 兼容性。分别改为固定运行时路径与流式 SHA-256 后重提。 |
| 98197 | [规则拟合与读回](reference-fit.json)通过，[OpenRCX 1.0 留出对照](heldout-v1.0.json)因耦合拒绝而返回 1。 |
| 98219 | 联合版图已读入。首轮[通孔样例](via-initial.json)把线段中心距当作有效线长，两个含通孔的总电阻各多 0.06 Ω。SPEF 中独立的通孔电阻均为 0.08 Ω。 |
| 98220–98222 | [2.0](heldout-v2.0.json)、[2.2](heldout-v2.2.json)、[2.3](heldout-v2.3.json) 都保留逐线对失败结果。 |
| 98237 | [通孔与线端对照](via-controls.json)通过。[#194 联合 296 网](coupon-296.json)的 SPEF 端点电阻连通检查通过。 |

Slurm 原始终态见 [slurm.txt](slurm.txt)。规则、结果摘要和运行命令见[正式目录](../../../project/experiments/m11_m12_rcx/README.md)。

## 后续验收

现有规则适合重现实验。整版寄生资格仍取决于跨层耦合修复后重跑固定留出组，并对同版真实互联做独立对照。#194 的宏视图为 LEF 抽象，且试布版本含两个代理端点。父层供电、时钟和系统 STA 随实际父层版图验证。
