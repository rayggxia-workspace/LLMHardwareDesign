# V失败源只读几何定位：两项实际通过

Refs #121 / PR #122。557/93744/node18两项16CPU任务同时运行（0–15及16–31），cap约6.6s、spacing约10.6s，峰值进程树RSS采样约1.48/1.71GB。不是六个独立ready任务时不造空任务。源f9ece579、归档527c843d；312份归档Git/远端SHA及receipt输入绑定，24原始小文件/15稳定本地输出，4,161,948字节完整spacing几何保留服务器并记录SHA，见index.json server_only。原ODB执行前后SHA相同。

523实际445个Metal Spacing标记对应436网，完整导出77732矩形（wire/via/BPin及变换后单元pin）和端点身份，无marker窗口遗漏。精确DBU分析：440个marker被一条同网wire矩形完全包含，445个全部被同网wire/via金属并集覆盖。只说明实际标记与金属覆盖关系；不能据此宣布DRC误报、豁免规则或接收。没有在标记处新增导体或修改任何原始源。后续需用同一实际检查器做隔离正反例，核对导入/同网多边形语义，再决定真实物理修复。

538电容网导出554矩形/13单元端点：驱动max_cap173361/Z为BUF_X4，下游11个BUF输入（7×X2、3×X4、1×X1）及一个NOR2_X1/A2。实际cap255.461563110fF>242.309997559fF仍拒收。此定位不等于已经修复；须以新552最终提取结果决定是否需要缓冲/尺寸ECO并重做全部物理门，不盲改RTL。

参考上游检查器代码仅用于理解查找方向：[FlexGC_main.cpp](https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/drt/src/gc/FlexGC_main.cpp)。它不是当前二进制版本证明；当前日志版本为unknown，实际工具SHA见两项receipt。不得把master代码语义未经验证套到实际镜像，尤其不能改检查器规则来让结果过门。
