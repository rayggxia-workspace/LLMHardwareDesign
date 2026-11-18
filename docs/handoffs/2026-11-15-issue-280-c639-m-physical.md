# Issue #280 C639 M 同源映射与布线接续

2026-11-15（Asia/Shanghai），仓库 `rayggxia-workspace/LLMHardwareDesign`，项目 `llm-hardware-design`，分支 `task/280-seven-model-energy`。负责人 Melodydt。映射源 `e0bee1338fb214bc53bbeee8806aef415c17e333`，当前布线源 `4d3f3535e5989d00242b7485c89962a9993f698c`。管理副本位于 `D:/Study_material/Study_material/LLMHardwareDesign`，交付走 Melodydt 的线上任务分支，原始大型工件保存在服务器个人工作目录。 [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281) · [M60 来源、反例和 C639 波形证据](../../work/Melodydt/280/C639_M_PHYSICAL.md)

已通过 `116953` 接口定向测试、`116958` 实际 C639 波形比较及 `116956` 内 18 项原生 M 叶块回归。固定的 M60 原始映射输入与 M60 物理验收源码一致。单元 test 的实际同拍 `START`／`ALLOC` 证明旧 M60 与当前 C639 的权重模块有周期差异；该双 valid 条件在原来的六个 C639 波形窗内出现零次。

服务器 `yuzelu@10.129.166.172`。`116956`（c64/node9，12 核，9 分 55 秒）已 `COMPLETED 0:0`，结果持久到 `c639-m-physical-02/map-116956/`。首个布线 `116957` 因目录参数退出。修订布线 `116976`（`mdt-280mroute`）在 c64/node9 以 12 核运行，实际目录 `c639-m-physical-03/route-116976/`。已读回映射清单通过及 OpenROAD 结构工件。 [终态和启动命令](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/8a58ca82721a50939f2e4e4e988d4a556b7a6e5a/work/Melodydt/280/C639_M_PHYSICAL.md)
 
```bash
cd /public/home/yuzelu/Melodydt/runs/issue-280
squeue -j 116976 -o '%i|%j|%P|%T|%C|%N|%R'
sacct -j 116956,116976 -o JobID,State,ExitCode,Elapsed,NodeList
tail -n 30 c639-m-physical-03/slurm-116976.log
tail -n 30 c639-m-physical-03/route-116976/route.log
(cd c639-m-physical-02/map-116956 && sha256sum -c mapping-results.sha256)
sha256sum -c c639-m-physical-03/route-116976/route-results.sha256
```

继续工作 的第一步为检查 116976 终态。已有 `C639_EXACT_M_MAPPING_PASS`、18 项叶块回执和清单。布线完成须有 `C639_EXACT_M_ROUTE_FLOW_PASS` 与包含 `6_final.v`、ODB、SPEF、SDC 的清单。布线候选还需核验 DRC、电气、时序、寄生及同源门级功能，随后用 C639 原工作负载取三路 M 的有效功耗窗。若物理失败，从 `route.log` 和对应阶段子目录恢复，再用实测差异评估调参。仍待 512-bit SRAM／PM 实际写路径、母控、局控、DMA、互连、时钟、专项对照、模型扩测及总能耗误差汇总。登记待合并，Projects 缺配置，PR 待独立审查。
