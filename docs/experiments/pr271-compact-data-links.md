# #271 方案 A 四组数据通路的紧凑版

> 历史版本：本页包含独立 reader 及外围块，共 14 个实例。按后续明确要求，当前交付已改为[仅九底座的原生接口版](pr271-nine-native-data-links.md)，四组顶层连线全部连通。本页保留原始结果供对照。

本实验延续 [#271 方案 A](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/271) 的功能块组织和 [#285 的前两轮布线](../../work/huangpingyang04-lgtm/250/pr271-data-link-routing/README.md)，对应 [Issue #250](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/250)。先用新版 C、U、P 的原生级视图闭合四组，再按 #279 示意图的相对排布压缩外框。P0、P1、P2 和 DMA 排在底部，C0、U0、U1 居中，F0 填入上排空位。

| 指标 | 四组闭合初版 | 紧凑版 |
| --- | ---: | ---: |
| 版图外框（mm） | 13.432 × 6.244 | 7.544 × 5.130 |
| 外框面积（mm²） | 83.8694 | 38.7007 |
| M11/M12 中心线总长（mm） | 2,020.8474 | 1,955.4378 |
| 顶层分支／独立网 | 1,053／1,049 | 1,053／1,049 |

| 顶层通路 | 已通过几何检查 |
| --- | ---: |
| C0.S ↔ U0.S，Attention 分数与概率 | 306／306 |
| P0.S → P1.G，Gate/Up | 335／335 |
| P2.S → C0 的 E32 远端读前端 | 206／206 |
| P1.S → P2 的 M 远端读前端 | 206／206 |

P1 采用 MY 方向，并以更疏的 M10 引出解除 Gate/Up 和 P1 读总线的交叉阻塞。紧凑版保留端口归属，分别缩短 P0/P1 通道 148.8 µm 和 C0/U0 通道 52.8 µm。独立校验核对了 1,053 个驱动端到接收端的分支、线距、孔距、边界及低层引出避让，14 个实例无重叠。KLayout 合版 OASIS 回读核对 2,102 个 V10 的 M10 铜覆盖及全部顶层路由形状。两个实体读前端原有 OpenROAD DRT 报告均为零违规，412 个 peer M10 端口与 ODB 导出表逐项匹配。

第 3、4 组到达实体读前端。前端到 C0.E32 和 P2 原生 `cp_*` 的实体接合、端到端提交和释放、P2.M 跨窗口累加回归仍待完成。整芯片工艺 DRC、LVS、寄生提取与 STA 待验证。仓库复核程序校验发布的 OASIS 指纹、几何和前端端口导出表。KLayout 重新合版、原生 ODB 校验及从头布线依赖授权服务器的冻结输入。

## 文件和复核

- [OASIS 版图](../../work/huangpingyang04-lgtm/250/pr271-data-link-routing/compact/271-repacked-four-links-compact.oas) · [布局预览](../../work/huangpingyang04-lgtm/250/pr271-data-link-routing/compact/layout.png) · [实际坐标](../../work/huangpingyang04-lgtm/250/pr271-data-link-routing/compact/placement.json)
- [逐位分支](../../work/huangpingyang04-lgtm/250/pr271-data-link-routing/compact/check/connections.csv) · [独立校验](../../work/huangpingyang04-lgtm/250/pr271-data-link-routing/compact/check/checks.json) · [合版回执](../../work/huangpingyang04-lgtm/250/pr271-data-link-routing/compact/stream-receipt.json) · [服务器来源索引](../../work/huangpingyang04-lgtm/250/pr271-data-link-routing/compact/provenance.json)

从仓库根目录运行以下验证命令。

```sh
python -B work/huangpingyang04-lgtm/250/pr271-data-link-routing/compact/verify_compact.py
```

如已从授权服务器取得两套原始 reader ODB，将其放在同一目录下的 `C0/extended.odb` 和 `P2/extended.odb`，通过 `--reader-odb-dir` 附加校验两套 ODB 的 SHA-256。作业 119248 完成初版闭合，119242 和 119243 完成接收前端布线与 BTerm 读回，119403 完成紧凑版 OASIS 合版回读。
