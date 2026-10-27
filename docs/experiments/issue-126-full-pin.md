# 全功能分块、全块二维 pin 与实际接入（Issue126）

任务：[Issue126](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/126)，进行中。
起点：[PR120](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/120)，已重新核实 open、未合并，head `4f91e098127b4320ce50dcb29165a7af1fca559c`。
本分支在其上增量提交，不合并或覆盖旧成果。

直接查看：[中文交互 HTML](issue-126-full-pin/report.html)。
图像：[ACT](issue-119-pin-xy/assets/act_comparison.png)、[MXU](issue-126-full-pin/assets/mxu_comparison.png)、[openTPU SYSTEM](issue-126-full-pin/assets/opentpu_aux_comparison.png)、[GEMM](issue-119-pin-xy/assets/gemm_comparison.png)、[VECTOR](issue-126-full-pin/assets/vector_comparison.png)、[llaccel SYSTEM](issue-126-full-pin/assets/llaccel_aux_comparison.png)；每块包含局部放大、真实端点图，新增四块PNG/SVG均入库。

复用 Issue55 已有真实 SYSTEM 包装补齐完整功能归属：openTPU 为 ACT/MXU/SYSTEM；llaccel_core 为 GEMM/VECTOR/SYSTEM。18项功能完整归属，两个父层未归属叶单元均为0。外部DRAM/host/封装、llaccel_core外部SRAM存储本体不虚构为已实现block。ACT+MXU合并版是替代粒度，不重复计数。

六块共24,767原始信号pin，A/B/C共74,301行；名称、位宽、方向、层、网络、矩形尺寸和逐pin对应保持。父层逻辑连接及对端pin原层已绑定；原父层真实handoff层/穿层路径仍未知。完整表、来源、候选/冲突/密度与阶段结果见HTML，不把几何L1当实际线长/RC/面积收益。

初步推荐：ACT/GEMM值得稀疏内部数据簇试验；MXU收益有限需局部对照；VECTOR本轮优先原边界；两SYSTEM建议选择性混合布局，全C冲突较多。单块保留边缘pin有可查询理由，不强迫全内移。

已在独立授权目录实际启动匹配8pin的A/Aopt/B/C重新接入，并增加原XY重布线控制A_replay。ACT已完成局部真实重接、fresh native DRC、选中网络真实几何连通及OpenRCX/独立边界STA；其他块按回执分别列示，未完成与失败不改写为通过。
完整全块连通、GDS/LVS/适用完整规则、版本匹配父层可访问性、完整系统RC/STA与电气资格仍待验证。

源码/命令：[full_pin_xy README](../../project/experiments/full_pin_xy/README.md)；完整候选覆盖回执：[coverage_gate](issue-126-full-pin/data/coverage_gate.json)；物理分阶段回执：[physical_summary](issue-126-full-pin/data/physical_summary.json)。
大体积ODB/DEF/SPEF保留于 `/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027`，远程源只读挂载，历史活动作业不修改。

验证入口：

```sh
python scripts/check_project.py
python project/experiments/full_pin_xy/validate_repository.py
```

ACT完整740-pin C现已实际完成接入和详细布线：提取前路由母本经独立进程native DRC=0、全块多端信号/时钟几何连通通过；独立边界setup/hold最差余量约1.259268ns/0.032872ns，电气违例报告为0，仍非完整系统签核。当前OpenRCX后的ODB序列化状态与DRC不兼容，已通过逐阶段对照定位并隔离，所有物理母本使用提取前routed/clean ODB，RCX/STA单独记录。新增四块候选按真实制造网格r02增量修订，r01与失败保留。

## 本轮独立C接入终态

下表只说明已执行范围；所有六块的当前C试验均独立clean native DRC=0、全块多端信号/时钟OpenDB几何连通通过。GDS/LVS、完整规则和真实父层接入均未由此通过。

| 块 | 实际C范围 | 独立块setup余量ns | hold余量ns | 当前模型结果 |
|---|---:|---:|---:|---|
| act | 740 pin（完整C） | 1.259268 | 0.032872 | 现有独立边界模型下通过，完整系统未验证 |
| gemm | 8 pin（局部；全C未实施） | 0.775029 | 0.051618 | 现有独立边界模型下通过，完整系统未验证 |
| mxu | 8 pin（局部；全C未实施） | 0.242632 | 0.051323 | 现有独立边界模型下通过，完整系统未验证 |
| vector | 8 pin（局部；全C未实施） | -4.166532 | 0.025641 | 实际时序/电气未通过，原基线失败保留 |
| opentpu_aux | 8 pin（局部；全C未实施） | -0.402281 | -0.382246 | 实际时序/电气未通过，原基线失败保留 |
| llaccel_aux | 8 pin（局部；全C未实施） | -2.153024 | -0.547887 | 实际时序/电气未通过，原基线失败保留 |

ACT相同740-pin cohort的原XY重布线/B子集/C：DRT提取前总线长271,186 / 271,833 / 253,825 μm，via为37,557 / 37,833 / 36,918。C比原XY控制组线长−6.40%、via−1.70%，setup余量略变差；这是单次真实路由统计，不是几何L1、RC或全系统PPA，也不能证明优于所有边界优化。外框相同，不计面积节省。

父层材料继续检查了Issue55的44份已完成parent/union/top元数据，5份含精确原叶ODB哈希，但这只提供placement等来源线索，仍未建立逐pin原始handoff/实际层序；不据此指派M8或宣布父层可访问。
