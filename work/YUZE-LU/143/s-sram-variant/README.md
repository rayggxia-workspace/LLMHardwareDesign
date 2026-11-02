# S 的独立 SRAM 接口候选

Refs [Issue143](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/143)。
本次旁支用户明确授权新增 SRAM 版并保留非 SRAM 版；只在
`task/143-s-sram-variant` 工作，不改原七块运行中的候选和队列。

2026-11-01 16:02 CST：新增独立S SRAM接口候选；四个256×128bit单1RW银行，保留128bit普通口、512bit宽读和原供数器。响应增加一级寄存，两个通道各有含在途预留的两槽容量；连续消费时每拍可接收一条读请求。三初态存储各2612687检查/54163拍、完整供数各54370检查/9448拍、257组描述符均通过，严格lint通过。原标准单元S/供数器/生产选择与正在运行的任务均未改。真实宏生成前置缺Linux配套KLayout/ngspice，已保存实际拒绝回执；没有真实SRAM GDS/Liberty、布局布线或300MHz资格。

主要文件：

- [SRAM 适配层](../../../../../project/rtl/s_sram/block_feed_s16k_sram.sv)：四银行、在途预留和响应保持。
- [完整 S 外壳](../../../../../project/rtl/s_sram/block_feed_s_macro_sram.sv)：继续使用原供数器。
- [接口与复现说明](../../../../../project/experiments/s_sram/README.md)：接口、时序、容量、复位及真实宏接入。
- [实际本地测试](result.json)、[缺工具回执](macro-generation.json)、[来源核验](verification.json)。

仿真显式使用双边沿功能替身；替身不能进入物理源列表。生产构建必须
提供真实 OpenRAM 生成的同名宏及匹配模型/Liberty/LEF/GDS/SPICE，不能
退回标准单元数组、黑盒空 GDS 或沿用非 SRAM 版本的物理资格。

规则：rayggxia-project-collab 1.0.0；账号YUZE-LU；基础commit见verification。
本地分支尚未发布PR，审查pending；登记及Projects看板未在本地交付核实，
未声称synced或已验收。此旁支不修改Issue143状态，不自行合并。
