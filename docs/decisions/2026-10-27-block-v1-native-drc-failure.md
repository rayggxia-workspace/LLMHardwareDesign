# 原生独立DRC失败与预制修复边界

Refs #121；2026-10-27 08:22 CST。094/92123于39:36、MaxRSS6480224K失败；其余14项门槛通过不能替代DRC。

61项：METAL10.2三项；天线M4两项、M6一项、M7八项、M8四项、M9四十二项、M10一项。完整原lyrdb SHA f50f815a188d5b0b105980214a0792228f0ffb0bc21e61d824bb3ce7f60221b1及逐项数值保留于work/YUZE-LU/121/results/run094-terminal；58项逐一复算ametal/agate与原ratio一致、超过固定300门槛。三项M10间距边对y=330.07/330.2 μm，相隔0.13 μm，小于deck的0.8 μm；仅凭坐标还不能确定所属网络或修复方式。

实际容器只读观察：技术LEF SHA834a79295054cd4209178d1bade67c353863c47bb4b3c22ee38b862b7cec37f2没有ANTENNA字段。macro.mod LEF SHA a43aea339f12a57a63497783e508ba16f3da2dc056d3247dec7d99707c2dedef有ANTENNA_X1，CLASS CORE ANTENNACELL，但ANTENNADIFFAREA=0.0，其他门脚没有gate面积字段。该观察尚不能证明实际ODB加载了这个单元或存在可用真实二极管；原globalroute警告没有可用ANTENNACELL，其零天线数不是完整几何证明。

后续先将每个marker对应到真实原生网络/路径/端口/门及扩散连通，核对完整GDS与库几何，再选择真实的预制阶段缓冲、接入重排或合法天线修复。技术/单元天线元数据若补充，必须由真实几何及规则推导、独立控制验证，不填写虚构gate/diode面积。所有有源修复计入面积/时钟/负载预算，A/C比较使用一致策略；新候选独立run，旧093/094原件只读。保持完整DRC和ratio300检查，不豁免违例、不把新层当作修改已冻结原生层的途径。当前未实现或运行修复，不发布合格硬宏；095原依赖失败保持未运行。
