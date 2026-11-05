# Issue #162：按当前原生引脚分组，保留既有物理宏和数量

对应 [Issue #162](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/162) / [PR #163](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/163)。本提交是默认关闭的候选连线修复；完整组合仍未通过，不合并。

原3200um S仲裁器已通过全部独立原生及固定PG验收，其他22物理类型和main六宏/R保留。source1772用旧1470um引脚保持原Link8分组，导致同组当前原生源引脚最大跨度2612um。原17750及平移18020/18120即使通过较弱必要电容检查，也不能据此认定可布通。

实际18020/18120的全部11149接点数组及345位置已下载并与本地候选逐项核对。原net_8939仅接收端的L1 MST为2853格；按[Hwang1976直角Steiner下界](https://epubs.siam.org/doi/abs/10.1137/0130013)，线长至少1902格。在现有同一RC模型和实际native/pin负载下，high总电容至少1934.569892fF，超过原1904.3fF上限30.269892fF。此结论只排除该固定接收端相对位置与复位分组；不表示项目或其他摆放不可行。没有修改任何电气门槛。

新增 `--link-current-pin-groups` 必须同时使用原R256、本地复位padding和已绑定的旧参考清单。参考坐标仅决定各source/destination组数；当前合格3200um原生引脚决定邻接lane，必要时把相邻组拆为小组以保持原数量。S仲裁器等价的复位负载沿当前源引脚周长排列，所有53路仍来自同一M1–M10复位状态、同一拍延迟。M11/M12只改变被动连线。

保持23物理类型、345实例、316个Link8、25复位bank和所有数据/控制/host载荷功能。没有新增物理块实现、没有修改native版图或RTL。局部对照最大源引脚跨度从2612um降至32um。新增分组会改变组合的连线，必须重跑实际Yosys、三初态八程序、内部/外部任务轨迹、native RC、所有最终M11/M12几何/XOR/PG及三档RC300MHz联合验收；旧组合资格不转移。

已执行：`python control162-groupcheck1831.py`，默认完整topology原字节及完整link证明序列化精确回放、新模式原始载荷精确收缩、原物理类型/数量不变、九项非法profile拒绝通过；四文件语法检查通过；`python scripts/check_project.py`通过。它们是源合同检查，不是布局布线或系统通过。

本地大输入保存在授权工作区 `D:\Data\电路实验\control162-math-data1790`、`control162-topology-data1825`、`control162-actual-steiner1829`；实际远程输入位置/字节/SHA见随附JSON。检查脚本为当时实际执行原件，内含本机路径，移机重跑需按收据重新实收输入并改工作区根。新的远程源码冻结、全文件/反向补丁审计及运行回执将在后续实际结果中补齐，不宣称已经执行。

规则rayggxia-project-collab1.0.0；登记PR5 pending；缺board.json，看板unverified/同步pending；审查人待指定；Issue in_progress / PR Draft。
