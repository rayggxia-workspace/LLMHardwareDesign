最新阶段与费用见 [2026-11-11补充进展](issue-250-native-progress-02.md)；下文保留早期阶段及证据边界。

位宽复核后，当前 S128 作为实际窄口对照。局部 S 的产品端口先验收四银行宽访问及关键 Dot 路径，再回校整图；旧宽口时序保留为历史参考。见[位宽对照与验收](issue-250-local-s-width.md)。

# Issue250：原生服务、控制和物理联合闭环

更新：2026-11-11，Asia/Shanghai。关联 [Issue250](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/250) / [PR251](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/251)。任务继续执行，未达到整机验收条件。

## 性能与硬件资格分别接收

旧条件 9.21564723269 token/s 和早期 NoPool 9.2237871361 均按公共 S 64 B/拍计费。只把该服务改为 16 B/拍时，同工作量 NoPool 降为 7.59543329637。后续 K-major、192 列投影、双 A 预取、尾组均衡等条件迭代达到 8.64696569673。各版本分别保留其接口、费用和覆盖，比较调度时锁定同一硬件。

保持公开模型/revision、36层、B1/context512 decode、W8A16、S32/Q16及51.2GB/s外存预算。总线读与逻辑读分别统计，数值任务与权重流量变化必须解释。算法改排程的收益、实际硬件支持变化、修正旧费用，分开比较。原生静态M不支持动态S32×S32 QK/AV；E/N等数值profile也需逐服务登记。即使条件计时超过门槛，仍不能跳过这些覆盖缺口或声称整模型可执行。

## 当前已实现的服务及边界

| 服务 | 原生证据 | 尚未证明 |
|---|---|---|
| 完整M/W/RF/scale | 四个1152B W寄存器银行、16×8 S32 RF、有限scope与描述符、128位短指令、256位A与512位DDR返回均进入真实RTL；根独立复核run19十八次数值/事件回执及117个文件SHA | 产品最终P&R、完整LC联接、动态QK/AV、全模型数值 |
| M租约 | INPUT EOP与RF RECORD EOP分开；CONTINUE不写S，FINAL/SPILL交真实两槽guard后等两次S128 ACK | 未识别owner的迟到transport错误归因正在修正；不能使用复用后bank的新owner冒认旧错误 |
| A与copy | 原16KiB S、2×256B A寄存器/P；同kk重放无额外S读；U/P0/P1/P2可选源，P三客户共用一S128口、两个响应owner；真实四源72次及router十八次回归通过 | 192列scatter、COPY scale控制帧、完整scope程序和最终物理 |
| G32叶 | 240×240µm，原TT300MHz setup/hold +81.264/+19.733ps，完整原版DRC0，最终ODB数值和严格等价通过；204/204 M10研究接入通过 | G外适配器与组合M11/M12电气/时序；G16到G32绝对面积增加，不能称更小 |
| G-S128 | 两输入/两输出槽共96B，真实128值读写到最后S ACK为107周期；新max探针从真实G输出观察shift，90次回归不改变107周期 | max逻辑及前端P&R，不继承G硬宏物理资格 |
| K128量化 | 同原S128、两个响应owner、32B打包寄存器；fallback扫描+重放共80事务，known-shift重放48事务。102168实测首请求至末ACK93/58周期，cmd至done95/60；错误返回真实写mask，取消/错误不声称回滚 | 完整LC/COPY/M联合和适配器300MHz |
| 量化→scale→A | 102186：六seed×三初态、两种背压模式，真实四bank数值回放、scale仅在16次真写ACK后发布，两个A use共用对应shift | 这是原生A操作数链路，不是整层或M计算数值资格 |
| scale目录 | 每对象最多32×6bit shift及valid/key；固定步长1/3分别对应X和三P条带Mid；重复/错owner/部分ACK/错误数值禁止发布 | 跨组元数据必须有真实帧和ACK；源各29/29/28项不代表接收方可常驻全部86项 |
| LC range | 六个真实issued metadata ticket、K-major/两way gate-up复用一个A lease；N1..7尾部、次序/地址界、OOO完成、held取消及故障排空，102160十八次通过 | record→M/guard真实生产桥；票从接收至RF提交/真SACK，不在INPUT ACK释放 |
| MC与LC程序存储 | 九真实resident/十六token/九event的MC、128位传输及双通道独立beat/descriptor credit primitive已有RTL回归；LC新增1KiB程序存储和CRC在独立实验推进 | peer回归不等于五类实际服务。真实descriptor取参、whole-FFN outer、循环指令、完整MC/LC程序/最终物理仍需联合验收 |

量化旧单在途实现的323/194周期和失败run均保留。新实现只增加8B打包寄存器并利用原响应容量；这属于实际前端实现改进，不能记作DP算法自身收益。`known-shift`只能来自已核验的生产者观察结果，不能把未测的X/其他算子默认设为known。详细逐请求/ACK夹具见[量化实测事件](../../work/YUZE-LU/250/quantizer/s128-events-102168.json)。

## 不增加私有SRAM，但逐项计控制和寄存器

NoPool 的容量预算为每控制组原有私有 S 16 KiB。当前窄口对照使用 `local_s_base`。四银行宽访问候选沿用这四个 1RW bank，接口逻辑和布线成本单列。新增或替换的 W4608B、RF512B、scope 约1152B、命令128B/返回64B、A512B、结果64B、G 前端96B、量化32B及所有目录、tag、mux、程序存储分别计面积。

scale目录是已实现的控制寄存器方案，不是S内字节写。X和Mid同时存活时可用两个有界目录；Mid接收方只把当前shift绑定两A lease。S内32条×16B宽目录及第17条S事务可以作为单独对照，不能将它的成本和寄存器实现拼接。COPY不能线性多读第17个Mid数据字冒充另一区域的scale。

P/U/C/F/J继续是独立宏与局控/适配器的控制归属。一个类型一个实现，布局聚拢作为软约束；不回到五种大硬框。M映射目前711030.502µm²、1296实际端点，完整逻辑API的5484位不是产品管脚；映射不证明频率。M最终版仍在原库/原300MHz约束下迭代。

## 真实闭环仍需完成

1. 以最终192列窗口/生命周期表落实P1/P2到P0的scatter地址和源保持，保留条带变慢的负对照。
2. scale沿真实COPY控制传输并确认；目录/A lease的key、kk、generation与数据前缀一致，不能用data ACK替代scale提交。
3. 真实128B scope取参、尾CRC、LC小PM、outer循环与M串行guard联接。直接展开模型调用超过MC16KiB，需真实循环或计费重装；不把主机发命令或全局数组读当免费。
4. 用这些同源程序/端点/有限事件校准SystemC，继续多轮调度改进，再进行数值与全系统回归。动态Attention及未注册profile必须实现或明确拒绝。
5. 最终M与全部变更适配器300MHz/密度/DRC/等价/ODB验收，之后五类实际程序和共同底座互联验收。M11/M12研究接入不替代联合电气、寄生和时序。
6. 硬件服务固定后接回通用DP，独立报告算法消融，再做能耗/时间和同范围ASIC/FPGA对照。

## 证据入口与重核

[G物理](../../work/YUZE-LU/250/physical/G32_RESULTS.md)、[M原生服务](../../work/YUZE-LU/250/weights/NATIVE_M_HANDOFF.md)、[MC](../../work/YUZE-LU/250/control/mc-native/README.md)、[range索引](../../work/YUZE-LU/250/range/index.json)、[量化索引](../../work/YUZE-LU/250/quantizer/index.json)、[G比例索引](../../work/YUZE-LU/250/g-scale/index.json)、[目录索引](../../work/YUZE-LU/250/scale-directory/index.json)。原始大映射包保留在授权项目存储，run09/run17的`large-artifact.json`记录原路径、bytes和SHA；其余小回执保留仓库归档。

本地仅离线核对，不运行EDA/RTL：

```text
python -B scripts/check_project.py
python -B project/experiments/block_local_native/audit_range.py --root work/YUZE-LU/250/range
python -B project/experiments/block_local_native/audit_services.py --root work/YUZE-LU/250/quantizer
python -B project/experiments/block_local_native/audit_services.py --root work/YUZE-LU/250/g-scale
python -B project/experiments/block_local_native/audit_services.py --root work/YUZE-LU/250/scale-directory
```

登记PR5仍pending，看板缺配置/权限为unverified、同步pending；沿用Issue7交接。PR251保持draft，Issue250保持in_progress，不合并或提前关闭。
