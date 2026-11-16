# 动态 high16 的原生操作数覆盖

Refs #219 / PR220；2026-11-09。此规则改变硬件服务覆盖，不改变整数程序、宏、容量或精度。

`native_lane_cover.py` 从已经通过来源检查的原生图识别以下完整模式：

1. M 用 K2、基向量 `[0,1]`、width16/shift0 提取动态 S32 记录的 high16；
2. 该结果不是可观察边界，全部消费者都是用它乘常量1的 K1 M term；
3. 将这些 term 改为直接读原记录、K2 乘同一基向量，保留系数、移位及其他 term 的 K。

其整数等式为 `s16(x[15:0])*0 + s16(x[31:16])*1 = s16(x[31:16])`。
其他 term 不能跟着从 K1 改为 K2；其高 lane 可能非零。分组兼容键、命令生成、原生参考和独立检查器均按每个 term 的实际 K 处理。
没有主机提取、免费打包、新选择器或新跨 S 通路；原生 feeder 的真实地址限制和每次写 ACK 仍适用。

`candidates(tile)` 返回可选记录；`cover(tile, selected)` 可以选择子集，默认覆盖全部合格动态提取。
静态 literal 输入被排除，避免把常量折叠记成动态搜索收益。
产物内嵌完整原图、SHA256 和所选记录。独立 `verify()` 不调用候选生成或改写函数，重新核对每条原始消费者及完整预期图，拒绝遗漏边界、嵌套覆盖和无关修改。

`resident_batch_graph.verify` 在此类产物上调用上述来源检查；有限 S 检查器再校验实际 term K、地址、上下文、复制、输出提交。
这两项都不能替代真实混合 K 的 RTL 验证。

运行入口：

```text
python native_lane_survey.py IMMUTABLE_PROGRAM_POOL SOURCE_IR FRESH_OUTPUT --width 2
python -m unittest test_native_lane_cover -q
```

调查保留原计划，比较新池的标量贪心、分组贪心/DP、布局贪心/DP、可选分散写回贪心/DP。
目前覆盖选择在调查前完成，尚未把“物化提取还是消费者直接取 lane”作为每个前沿的动作；不能将本轮改写收益宣称为 DP 的额外收益。
下一步需要把表示、源记录活跃期、S 副本和必要写回一起纳入前沿，且给贪心相同动作。

本轮已验证原始 Qwen FFN 来源切片的两行冷程序：7组合成输入及3组此前完整模型执行导出的真实边界输入，包含四种 SRAM 初态和实际错行/错 K 故障。
真实边界版本保持原外部地址预算；不表示已完成新完整模型、所有元素循环、母控/局控/DMA集成、SystemC/DRAM/能耗/token/s 或最终物理验收。
证据与失败记录见 `work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_24.md`。
