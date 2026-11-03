# 七宏接口研究路线与P1源码选择

任务：[Issue151](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151)；交付：[PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)。日期：2026-11-01 Asia/Shanghai。状态：用户已指定研究路线；P1合同与材料待独立审查，未冻结硬件。

采用[七阶段路线](../SEVEN_MACRO_INTERFACE_ROADMAP.md)：P1版本/接口/参考/验证范围，P2最小MST与控制骨架，P3 E/G与FFN，P4 N与Softmax，P5拓扑复用，P6 R/NUM与有限状态原型，P7八样本/实际规模/MEM及共同底座验收。本次仅实施P1。

本轮源码保留研究分支已导入的643c6012a11cbf461146ac40fbf61485223fe946。与PR144在2026-11-01 14:00:34 +08:00读回的adb819c4d49516008e971a201a7d52c0248df8f9对比，14核心路径中13个Git blob相同，仅R实现不同；七个规范化顶层接口均相同。R的S128数值中间量修改仍需数值、周期与物理证据，不能仅凭端口相同自动导入。本轮不接管Issue143物理资格工作。精确来源、指纹与升级要求见[版本比较](../../work/Melodydt/151/phase1-version-comparison.json)。

P2首个测试输入选择S8×S8、K8/N8、一行一tile，M的S64结果原样经S进入T，避免首个闭环同时依赖E/G数值转换。192B S预留和64B T载荷仅是最小测试范围；不替代实际模型存储，也不取消系统外存。P1的软件参考与静态检查不能充当组合RTL验收。

继续保留共同M1–M10有源底座、M11/M12永久选择有限产品程序/路径的目标。类型、角色、尺度和布局主要由编译期合同核验；运行时所需MUX、保持、控制、计数和算术必须实际存在。后续升级按[第1步报告](../PHASE1_INTERFACE_BASELINE.md)登记差异，重跑受影响验证后审查接收。
