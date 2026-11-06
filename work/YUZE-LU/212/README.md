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
| 98803 | `smoke-fYrssZ` | P 仅暴露离轨 M10 落点同网 M9，绕过原 b_data[139] 失败，随后在缺 M9 平面导体的 b_data[143] 受阻 |
| 98829 | `smoke-k5EbkN` | 加入两级复位释放同步后，P/U 的母局控直连镜像和 U 五场景再通过 |
| 98832 | `smoke-xmH3rG` | 带局控复位同步的 U 物理候选，源包 SHA-256 `c64594a885cc98e724870224497d09dd8622cde0b73e29d08d1ae56823dd3d4d` |
| 98837 | `smoke-PEhKJ4` | P 实例几何、离轨落点同网 M8/M9 接入以及局控复位同步，源包 SHA-256 `ca783de7c8203b9571d4d5d5482cc5bc40af2df0f393cf0d4e4281fcd7316e91` |
| 98797 | `smoke-u9hJYX/resume-98775` | 完整原生 GDS 规则集完成。40 条报告为 VIA6.2，224 条 VIA9.2，9 条 METAL10.2，20 条天线违规。该样片未通过完整原生验收 |
| 98848 | `smoke-YDPl2E` | U 紧凑候选将 N/E 并排置于 S 上方。源包 SHA-256 待最终记录 |
| 98852 | `smoke-u9hJYX/resume-98775` | 130 根 U 上层候选线经 GDS 回读逐网验证，无跨网几何接触 |
| 98856–98859 | `smoke-2mnJxq` | 固定 CTS 检查点，分别检验 M9/M10 的 via-only 接入约束 |
| 98861 | `smoke-MesdcO` | 对 M/N 的低层 LEF 障碍增加保守包络。M/N 的 pin、上层几何、GDS 与 Liberty 保留。源包 SHA-256 `6087291b540f9a8ae1a8971af508d1bf93eb59b05fdabcf238ed0c7b19118565` |
| 98877 | `smoke-2mnJxq` | 由最终 GDS 递归定位。父层切孔与 S/N/E 叶宏切孔存在交互，M10 报告落在父层信号与供电间距 |
| 98879 | `smoke-oEBTpT` | 加入叶宏真实 cut 障碍、父层间距保护和标准天线二极管候选。源包 SHA-256 `a51296a65b9f7576a5ef1287072a530d1e530ac4408f3168b3961b98602000cc` |
| 98892 | `smoke-vQzl6X` | Block ID 与拓扑 ID 改由底座配置输入绑定。P 的直连以及 C 参考↔U 的五个模式均通过 |
| 98902 | `smoke-58RYV3` | 同时使用拓扑绑定、紧凑障碍视图和原生规则保护的物理候选。源包 SHA-256 `d60a0f4b2f249de62ce487d5afbcb6fd9148985be4df43208a79fd9729acddf3` |
| 98908、98909 | `smoke-58RYV3/fixture-{2,3}` | 两份带配置输入的 Yosys 映射网表运行原母控及程序镜像。P 一项与 U 五项全部通过 |
| 98917 | `smoke-3WQbtf/upper-sta-98917` | 98775 U 服务样片的上层复核。各 RC 档标注 130 根线、报告 20 条穿越路径。完整原生 GDS 状态仍见 98797 |
| 98932 | `smoke-rmEFT2/probe` | 从 98775 U 最终 ODB 导出真实驱动和接收器，独立核对 260 个 M10 接点的几何隔离和 130 对上层线。沿用 98797 的原生 DRC 结论 |
| 98927、99028 | `smoke-58RYV3/result-41` | U 最新受控候选详细布线末次零违例，最终网表母局控五场景通过。提取 setup +334.307 ps，hold −21.200 ps。完整原生规则审计另行执行 |
| 99029 | `smoke-58RYV3/result-42` | U 备选详细布线末次零违例。独立提取 setup −62.814 ps，hold −28.491 ps |
| 99016、99054、99055 | `smoke-HSp1jl` | 按实际提取结果在接收分支加 BUF_X1，保留原 CTS、原 STA 约束、天线保护和叶宏。源包 SHA-256 `b1f8bb95483a2203a65f6b092aa53a11b558270b847a7859cd53f358fd01d285` |
| 98924、98927 | `smoke-58RYV3` | 36 的 P 和 41 的 U 均由最终网表运行原母控、局控和 SRAM 程序，分别通过 1 项和 5 项 |
| 98925 | `smoke-58RYV3/result-41` | U 原版完整 DRC 报告 12 条 METAL10.2 和 2 条 WELL.4。原生 DRC 尚未通过 |
| 99199、99214、99221 | `smoke-PqiCiY/resume-99199` | U 真实提取 setup +277.009 ps、hold +11.220 ps，电气和 PG 通过。最终网表五项通过。原版规则子集报告 4 条 METAL10.2、1 条 VIA9.2、2 条 WELL.4 |
| 99200、99215 | `smoke-1S69D0/resume-99200` | P 真实提取 setup +11.344 ps、hold +22.959 ps，PG 与最终网表程序通过。仍有电气与几何违规 |
| 99217 | `smoke-WZVe5D` | P/U 各两份叶宏物理候选加入隔离行。源包 SHA-256 `47947c136210c05bde5614bc850f1dbd232897e11f05ca53dbf2f5afb9043c46` |
| 99231、99244 | `smoke-lC3Len/resume-99231` | P 定点驱动调整后，真实提取 setup +19.019 ps、hold +24.583 ps，电气和 PG 通过。仍有几何违规 |
| 99234、99238 | `smoke-VPo9ky/notches-99234` | U 两个同网真实 M10 缺口修复后，原规则子集 M10.2 为零，仍有 1 条 VIA9.2 和 2 条 WELL.4。完整原生验收未结束 |
| 99257、99259、99265、99270 | `smoke-FA6vym/notches-99257` | U 合并候选的原版完整 GDS DRC 为 0，原生 setup +269.804 ps、hold +9.023 ps，电气和 PG 通过。最终网表五场景通过。上层三档 RC 均通过，130 根线全标注。99259 在 DRC 后的汇总命令有引号错误，独立 check_native.py 复核了同一原始报告 |
| 99294、99295、99301、99302 | `smoke-LYLYBe/notches-99294` | P 保留原有有源布局和信号走线，用填充行窗口和真实同网 M10 修补。原生 setup +19.019 ps、hold +24.583 ps，电气和 PG 通过。WELL.4、VIA7/VIA9、M10.2 定向原规则子集为零，原版完整 DRC 另行执行 |
| 99301 | `smoke-LYLYBe/notches-99294` | P 完整原版 GDS 只剩 1 条 METAL9.2。与父层冗余 VDD 过孔栈相关 |
| 99313、99315、99316、99317 | `smoke-aOT4M1/notches-99313` | 移除经定位的完整父层 VDD 过孔栈。P 原生 setup +19.019 ps、hold +24.583 ps，电气和 PG 通过。M9、M10、VIA7/VIA9、WELL.4 原规则子集为零。最终网表及上层复核另行留档。99314 执行修复版完整原版 DRC |
