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
