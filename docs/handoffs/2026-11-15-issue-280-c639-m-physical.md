# Issue #280 C639 M 同源映射与布线接续

2026-11-15（Asia/Shanghai），仓库 `rayggxia-workspace/LLMHardwareDesign`，项目 `llm-hardware-design`，分支 `task/280-seven-model-energy`。负责人 Melodydt。当前源 `e0bee1338fb214bc53bbeee8806aef415c17e333`。管理副本位于 `D:/Study_material/Study_material/LLMHardwareDesign`，交付走 Melodydt 的线上任务分支，原始大型工件保存在服务器个人工作目录。 [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281) · [M60 来源、反例和 C639 波形证据](../../work/Melodydt/280/C639_M_PHYSICAL.md)

已通过 `116953` 接口定向测试、`116958` 实际 C639 波形比较及 `116956` 内 18 项原生 M 叶块回归。固定的 M60 原始映射输入与 M60 物理验收源码一致。单元 test 的实际同拍 `START`／`ALLOC` 证明旧 M60 与当前 C639 的权重模块有周期差异；该双 valid 条件在原来的六个 C639 波形窗内出现零次。

服务器 `yuzelu@10.129.166.172`，提交根 `/public/home/yuzelu/Melodydt/runs/issue-280/c639-m-physical-02`。`116956`（`mdt-280mmap`）已在 c64/node9 用 12 核运行；ABC 映射日志持久到 `map-116956/mapping/m_native_leaf_s32/map.log`。`116957`（`mdt-280mroute`）提交 12 核，以 `afterok:116956` 等待映射，启动参数和时限在回执中。映射失败时 Slurm 取消依赖布线，当前工作由任务发起人继续接续。

```bash
cd /public/home/yuzelu/Melodydt/runs/issue-280/c639-m-physical-02
squeue -j 116956,116957 -o '%i|%j|%P|%T|%C|%N|%R'
sacct -j 116956,116957 -o JobID,State,ExitCode,Elapsed,NodeList
tail -n 30 slurm-116956.log
tail -n 30 map-116956/mapping/m_native_leaf_s32/map.log
tail -n 30 route-116957/route.log
(cd map-116956 && sha256sum -c mapping-results.sha256)
sha256sum -c route-116957/route-results.sha256
```

继续工作的第一步为检查 116956 和 116957 终态。映射成功须有 `C639_EXACT_M_MAPPING_PASS`、18 项叶块回执和清单。布线完成须有 `C639_EXACT_M_ROUTE_FLOW_PASS` 与包含 `6_final.v`、ODB、SPEF、SDC 的清单。布线候选还需核验 DRC、电气、时序、寄生及同源门级功能，随后用 C639 原工作负载取三路 M 的有效功耗窗。若物理失败，从 `route.log` 和对应阶段子目录恢复，再用实测差异评估调参。仍待 512-bit SRAM／PM 实际写路径、母控、局控、DMA、互连、时钟、专项对照、模型扩测及总能耗误差汇总。登记待合并，Projects 缺配置，PR 待独立审查。
