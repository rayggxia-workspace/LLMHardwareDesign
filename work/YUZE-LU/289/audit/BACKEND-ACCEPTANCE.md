# A/B 非 P 接口 X8 后端验收

2026-11-18（CST），Issue #289 / PR #290。宏/block工程验证完成，进入独立审查。

两套归档方案的 **340个唯一目标输出全部为单一BUF_X8驱动**：C153、U153、G33、F内S1。方案A覆盖306个，B覆盖340个。输入作为接收端，信号端口形状、宏位置和外形保持不变。

| 实际父block | 名义频率 | setup裕量 | hold裕量 | 完整原版DRC |
| --- | ---: | ---: | ---: | ---: |
| C-v43-margin-plan0（含G hold03-v3） | 250MHz | +6.340040ps | +1.990130ps | 0 |
| U-v19-preserved | 250MHz | +78.050904ps | +3.471112ps | 0 |
| F-eco-h20-v4（含S minimal-localv4） | 300MHz | +221.605405ps | +2.453537ps | 0 |

Nangate45 TT，0.1ns时钟不确定度。C/U采用本任务冻结的I/O契约：目标输出50fF，其他输出2fF；非时钟输入/输出min/max延迟0.2/0.8ns，输入BUF_X2、50ps源slew。F沿用冻结原SDC，名义3.333333ns序列化为更严格的3.3333ns。上述裕量较小，特别是C和F的hold；结论限定于相应单角和独立块约束。

setup、hold、电容、slew、fanout均零违例；PG、异步控制、功能/状态/控制、信号接口几何、宏视图导出及重载检查通过。C最终实际网表SHA256为`2b74fbc9009a57b54f177c89a929a08abfadff7f566ed56928b0ce1441606e77`，从实际ODB重新导出并逐字节绑定后证明。原RTL到综合边界采用有限SAT/归纳、通用等价及明确列出的人工组合证明，不声称全模块RTL SAT或四态X等价。

C完整未修改FreePDK45规则检查120303耗时2h20m59，最终0项；独立同源物理证据复核120326通过，root精确裁定后最终聚合120366通过。278701条网络提取前后全层及过孔材料一致，SPEF对应实际几何。Liberty、零膨胀物理LEF和父级布线抽象的单位、方向、引脚/外形、上层OBS与实际cut覆盖通过。

C的fresh native报告保留222个M2/M3 spacing标记：每项由本网络及实际GDS连续金属覆盖，原局部space/notch检查零项，再绑定完整原版规则0项后精确裁定。F保留40个历史标记及4个逐项证明的同网宏接触标记。原生报告不是空报告，也不构成一般规则例外。

C供电边界相对原CTS移除230条、增加140条BPin记录，逐项追溯到v16/C35合格PDN基线；当前ODB/GDS重新确认同名电源覆盖、异名电源不相交与双轨连通。信号引脚保持原几何，U供电边界差异见其回执。

## 冻结交付与复核

[联合发布索引](evidence/AB-X8-final-joint-release-index.json)绑定C/U/F接受回执、G/S叶宏、340端口清单及root裁定。旧覆盖快照中C未接受标志保持原样，新的联合索引将其绑定到当前已接受版本。

- [C回执](evidence/C/accepted-parent.json)及[清单](evidence/C/manifest.json)：远端`audit/C-final-release-v1/`。
- [U回执](evidence/U/accepted-parent.json)：远端`audit/release-candidate-U-v19-preserved/`。
- [F回执](evidence/F/accepted-parent.json)：远端`gs/candidate-S-minimal-localv4/parent-F-eco-h20-v4/release/`。
- [发布只读重验](evidence/AB-X8-final-readonly-verification.json)：120368完成，58个实际交付/证据文件SHA匹配；此步骤不是重新运行EDA。

远端根目录为`/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117`。C包冻结ODB、DEF、Verilog、SDC、SPEF、GDS、配置、Liberty和两种LEF。大件在授权服务器，仓库保留小回执、脚本及SHA索引。只读重验在计算节点执行：

```bash
sbatch /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/verify-AB-X8-final-release-v1.sbatch
```

本次范围为宏/block后端。P相关网络、两套方案实际顶层长线RC联合STA、串扰和多PVT尚未纳入。B的G/S压力测试连线不自动成为产品级协议实现；不能由本表推导毫米级连线已通过200/300MHz。

项目协作按rayggxia-project-collab 1.0.0：PR待独立审查，Issue进入in_review。管理中心登记PR5仍open/未合并；Projects缺read:project及board配置，状态unverified、同步pending，沿用Issue7持久交接，由有权限管理员处理（待指定）。协作缺项不改变上述宏/block工程证据。
