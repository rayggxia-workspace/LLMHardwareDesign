# W5-IF：先建立有界三层合同，再实现新端点

状态：proposed，逻辑合同v0.1已形成、待外部审查；Issue151 / PR152；Melodydt；2026-11-02 Asia/Shanghai。输入commit f9a90c845504b198cc3265106e03c67902382ebb。

问题：现有MST/A8/F8的host帧、数值、输出和释放语义不同。将相同128bit载体视为通用hidden接口，或者把T的take/DONE当成目的存储完成，都会使功能岛链错误。M11/M12被动连接无法在冻结后增加存储、解析、协调器和控制程序。

决定：母控管理粗任务和全局资源，local独占本岛宏原生命令与存储口，新预制端点负责offer/payload、独立stored ACK、源保留与实际释放。有限产品的role/format/Fin/layout通过静态入口/程序表准入，运行时保留必要任务关联、真实计数、所有权和错误状态。母控固定控制网、模型相关data/ACK的M11/M12绑定仍为候选；最终拓扑、物理pin/中继/CDC需反馈后冻结。

首个实现目标只接收有界B8协议例：一母控、两岛、单时钟、每岛一个active任务、全局一个未关闭fragment、一字16B。SOURCE_COPY_H8→SINK_READ_H8是待实现的新入口；反向产品使用同一能力并集、另行永久绑定。这不是现有A8/F8串联或样本模型缩小版，也不证明共同底座已具物理资格。

命令捕获与准入分离：wire valid/ready使记录进入inbox，TASK_ADMITTED确认任务已准入。非法命令保留原命令关联并产生CMD_REJECT，不能冒用active任务的first-error/partial/sat。任务binding从成功ARM准入保持到REUSABLE握手。数据必须先预约consumer完整生命周期资源，真实目的S写ACK之后才能发stored ACK，producer收到有效确认且CLOSE后才能释放。错误不承诺撤销已接受写或输出。

代价：新holding、事件pending/latched、CMD rejection状态、parser、关联/计数、cohort恢复与程序都必须预制。64bit CMD/EVT/ACK、128bit数据载体的首例每岛536逻辑端点bit、82B显列记录holding；加入母控记录、26事实与9拒绝状态后819bit/岛配对仍不是完整控制器面积。实际S槽、whole tensor、权重/状态、ROM及物理开销另计。

完整产品仍需解决A8的hidden→QKV、F8的S16残差/Norm输入或显式新量化profile、Nctrl超过257及真实工作集/供参；R/MoE/MEM后续扩展保留GAP。单token H3072/S16能放进T不说明三份Norm工作集能放进S。外存仍允许存在，不作为当前轮隐含免费能力。

退出条件：本轮只交合同及静态来源/字段/算术核验，没有新增RTL/服务器仿真或物理验收。继续L4细化完整A/F有界计算与数值/存储映射；L5实施W2-C/W2-D/W6，L8做W10/W11最终系统和共同底座验证。合同与示例见[主规格](../W5_IF_INTERFACE_CONTRACT.md)。
