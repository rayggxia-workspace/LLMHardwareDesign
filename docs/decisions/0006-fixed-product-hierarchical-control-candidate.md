# 0006：固定产品的两级控制与分散适配（候选）

- 状态：**proposed / 待独立审查**，不是accepted，也不表示实现完成。
- 任务：[Issue151](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151)；交付：[PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)；负责人Melodydt。
- 前提：用户确认同一M1–M10底座在M11/M12定制时选择模型，成品运行不需要任意改图；不改变0004的制造边界。

## 候选取舍

1. 有限固定程序顺序器＋局部FSM代替通用在线DAG/乱序调度。主候选预置已接收产品程序ROM，定制连接产品选择端；一次装载控制存储为备选。完整产品程序、参数及容量必须在共同底座冻结前编译接收，六模板不能充当八整模型程序。
2. 一个母控管阶段/依赖和发布，各资源子控唯一驱动原生端口；Attention/FFN等为子程序，共享M/S不归多个算法控制器独立发令。先两级新增控制，区域层在更大规模物理结果支持后决定。
3. S中转及已有loader作为功能基线，bridge分散贴近宏，S仲裁贴近S；支持逻辑全部预制计价。新增NUM系数/宽归并显式列为计算能力。
4. 首版fail-stop并排空；不承诺M整命令回滚或R/T联合原子提交。R只有有限tile，完整GDN/SSM需外部版本化状态/历史与发布协议，单tile验收和完整token验收分开。

## 理由、代价与验证门

固定产品可减少运行时调度状态；局部执行可减少逐包跨区控制，但增加局部寄存器/事件路径；固定ROM占用全部支持产品代码；物化增加存储流量；新增版本服务/NUM有真实面积和外存成本。以上均无本轮PPA实测。

冻结前比较中央、母＋局部、母＋区域＋局部三个不同底座候选；选定后再固定有源几何/PG/CTS，仅改变允许定制层验证至少两个产品。不得为不同产品各自插新buffer修时序。程序完整性、容量、类型、资源租约、事件/取消、数值和物理检查通过后，才可把候选改为接收方案。

详见[总方案](../SIX_CONNECTION_SYSTEM_DESIGN.md)、[控制规格](../SIX_CONNECTION_CONTROL_SPEC.md)、[模板规格](../SIX_CONNECTION_TEMPLATE_SPEC.md)。本记录不修改既有叶宏任务、服务器或ref-project。
