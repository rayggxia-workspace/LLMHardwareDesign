# Issue #212 P/U 工作记录

负责人 YUZE-LU。基于 main `7e5da80a26e324b85e092671e1b66edfdd34cc48`，分支 `task/212-pu-leaf-base`。服务器证据位于 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-212-pu-leaf-base`。

| Slurm | 证据子目录 | 源包 SHA-256 | 实际结果 |
| --- | --- | --- | --- |
| 98626 | `smoke-bhwMqG` | `9b378f0aee54e0b7441496a72763a72d213b233b281870b85540666d62090c0d` | 原生 P/U 和两个服务回归各三种初态通过 |
| 98558 | `smoke-S7icXY` | `1a1d402610bb742cc8d9b72136f035237b7fe51c5aa69bfb2d3dc89c7bd4063b` | P 母局控单组及 C 参考组↔U 的五个场景通过 |
| 98618 | `smoke-n1zwlu` | `d096e4eb89b434f4670cc2a940d767fac79e6abc010b09467df61827f83d3654` | P 一项进入路由，停在 S_P M10 pin access，其余候选停在 CTS hold 修复 |
| 98633 | `smoke-9ioom3` | `d63111de47e3e82f8a7282514b8d37c156c22e18ef40d32fcb460f8725e4397a` | 增加 PG 过孔避让和四种 CTS 设置 |
| 98642 | `smoke-vMvnRF` | `a2437bd0858595a57a67f88e8bd6372ae739612f5c54f7c2fe5b0f0a744117b1` | 使用同网 ODB 导体生成接入视图 |

参考 #203 双型 S、#205 紧凑 G/E、#195 控制基线和 #190 的 M 物理视图。复跑使用固定 ORFS 容器。作业日志保留节点、核数和亲和性，`inputs.json` 记录叶宏视图 SHA-256。项目登记沿用 management-hub PR #5 pending。缺少 `config/board.json`，看板同步待项目管理员核验。独立审查待指定。

| 后续 Slurm | 证据子目录 | 实际结果 |
| --- | --- | --- |
| 98711 | `smoke-7IJFV8` | 原生 P/U 及两个服务的三初态通过。U 配对覆盖背压、源失败取消和未启用拒绝 |
| 98717 | `smoke-CsMnNF` | P 与 C 参考组↔U 的 #195 母局控 SRAM 回放通过 |
| 98730 | `smoke-ipEtOk` | 可编程 P 执行 M→G 直连，真实 SRAM 最终写回匹配 |
| 98721、98722 | `smoke-NROX0F` | 两份 U 原生服务样片详细布线末次零违例。补齐 CTS 续跑所需的合成参考网表后，分别用 98732、98733 生成最终 GDS 与独立提取，setup +469.100/+414.134 ps，hold −29.136/−32.158 ps |
| 98737、98738 | `smoke-smfM8m` | U 原生样片提高路由修复裕量并完成详细布线。98737 的独立提取 setup +378.389 ps，hold −2.343 ps |
| 98764 | `smoke-z0iYyE` | P 和 U 的直连程序经过母控、局控、真 SRAM。U 五种模式均通过。复用 #195 的 4096 周期局控 watchdog |
| 98775 | `smoke-u9hJYX` | U 原生服务样片完成布线和 GDS。独立提取 setup +369.349 ps，hold +15.796 ps，未报 max slew/cap/fanout。完整原生 GDS DRC 由 98797 执行 |
| 98798 | `smoke-o5MUYb` | 98775 的最终原生服务网表加真实 SRAM、N/E/S 功能模型，三初态回归通过。沿用该版兼容的原生服务测试 |
| 98799 | `smoke-o5MUYb` | 98775 的 130 根上层几何连接与 M1–M10 SPEF 合并。研究模型三种 RC 均给出 setup +374.118 ps、hold +15.796 ps，未报 max slew/cap。仍需最终控制版、真实顶层互联和规则验收 |
