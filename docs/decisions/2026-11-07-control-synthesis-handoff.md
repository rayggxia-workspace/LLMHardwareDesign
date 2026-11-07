# 以九种现有配置冻结控制综合交付，保留真实原生实现清单

Issue179 / PR180；Melodydt；2026-11-07 Asia/Shanghai。

第9步采用既有five_boot_top（KIND0-4）及recovery_boot_top（KIND0/1/2/4），不引入新产品拓扑。PM_USE_SRAM固定1；64 bit执行ISA与3.333333333 ns目标不变。现有控制源按第8步SHA锁定，参数与目标注册表交叉核对。

交付包分开保留完整原生RTL文件清单和控制分区清单。后者以原生group的真实端口声明为逻辑边界，不把group假定为组合硬宏；真实宏、S/T和计算数据路径仍在全RTL中。三个PM各四bank，共12 bank可在控制层次实际核验；这不代表全芯片只有12个SRAM。功能bank含仿真延迟，只用于全RTL展开，综合必须用声明边界，不能无意综合成寄存器阵列。

标准单元Liberty/LEF、输入bank及原生来源锁有逐项SHA。SDC沿用既有I/O、uncertainty、转换及负载预算，无false/multicycle路径，复位仍受约束。OpenSTA序列化周期采用内部浮点表示，读回容差1e-6 ns（1 fs）仅处理表示误差，不修改目标周期。检查对每个实际顶层端口核对max/min及输出负载。

当前完成的是结构、来源、约束对象及可搬移交付验证；port-only接口夹具不能给出组合WNS/TNS。原生group/SRAM的物理时序视图、完整叶宏绑定、同版映射/组合STA、等价及物理实现另行验证。既有独立组时序资格不能转移。第8步功能矩阵是前轮证据，本轮不冒充重跑。

首次归档缺来源索引、OpenROAD缺tech LEF初始化及序列化数值字符串假设的失败均保留；修正交付工具，未删检查、修改控制RTL或放宽周期。复现命令和证据见project/control_presynth_v1/README.md及work/Melodydt/179/control-synthesis-freeze-validation.json。
