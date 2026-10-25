# Issue80 Block电路首轮冻结协议

2026-10-25 UTC+08，Liangruizhi/182389313，Issue80；base PR77@889ca420181c932598c8e70c500dcdb01156b59c。用户批准计划1—3：参考/规格、完整宽控制器与有限frame、同资源内部连接比较。真实模型/数据/RTL/综合仅本人CPU服务器Slurm lrz-i80-*；PC只源/微合成/JSON/字节。无新模型/其他机器/软件安装/成员55和63接管。成员63/PR79软件已in_review，物理绑定仍待资格；不把它当实际布线完成。

## 冻结电路与可证范围

8条S8/byte ALU，按命令lane号选择其中1条执行标量；8×5B输入/输出latch。主frame512B、32行×128bit单1RW、无byte mask，字节写须读旧行+整行写；局部与BUS候选都同容量同端口。新RTL负责PC、取指缓存16B、指令译码、操作数读取、ALU发射/返回、逐字节RMW、4层有界CALL/RET、状态/标签/错误/完成保持；不能由host逐动作调度或写入中间数学结果。

64bit静态微指令从显式外部程序存储读入，128bit单读写接口、2指令/缓存行。所有数据运算仅byte/S8指令；多字节寻址/PC计数等是明确的控制电路，不充当数据宽ALU。程序按opcode/有限shift域编译，与输入数据值无关；编译器须对原807case逐项验证拓扑不依赖值。常量/程序可预装载，但程序字节、地址表、装载下界和运行时每次取指均单列入账。程序不默认为免费的无限ROM或寄存；动态shift由RTL CALL地址表选择，不由host逐输出选择程序。

18typed函数沿用76 micro.py原整数算法，边界/132真实Granite样本/全有限shift域807case原值复用；新独立数学oracle判有效码，溢出/零除仍valid0。非法opcode/PC/CALL栈/ROM地址或链内guard失败给命令error，不静默饱和。命令完成/status/tag保持直到ack，busy期间禁止cfg写frame。reset只清控制/未提交命令，不清SRAM，不允许reset后发布旧完成。

单32bit ROM深32768、131072B实际保存原73736B LUT+padding，所有请求/返回及写frame有真实控制；功能延迟与工艺时序分列。两个候选共用相同controller/ALU/ROM/程序与frame；区别为frame直接局部端口，或经有界串行memory/BUS bridge。bridge有实际RTL状态/暂存、ready/valid和明确服务拍，不将其当工艺线长。程序取指始终经过相同外部bridge，不能从局部候选漏去取指/控制费用。

## 冻结最小实验

2组织（BUS frame/local frame）×2环境（无附加外存背压/确定种子背压）分别新out；每个执行807原case+ROM请求+负例/复位/完成保持。主排名仅同环境同程序的两组织，绝对周期不与76条件slots横排。关键小链覆盖INT32→scale/RNE、完整8专家单坐标merge/残差、缩小完整norm行（8元素）与动态shift130/131译码。它们是电路数据依赖闭环，非完整1536hidden、真实M阵列或整模型质量；旧43stage软件数学保持独立证据。

先完成pilot和独立核验，再并行4配置。报告真实cycle、取指/数据读写、bridge字节/拍、局部端口动作、ROM访问、所有有限存储/寄存和cell统计。若映射到不同RAM/额外端口需作为不同资源候选，不宣称同面积。对相同源做Yosys检查、memory位数与乘法器宽度检查；若无宏/工艺资格，输出通用cell与存储位数，不声称STA/PPA。物理布局、目标频率/PVT、SRAM/ROM宏和M8/M9/M10接入需后续冻结，不擅自接管55。

源码/配置/input/outputSHA、独立拒绝负例、实际Slurm、失败与修复、新out、归档/接收、PR和进度/交接须完整。登记PR5 pending；无board/Projects则unverified/sync pending，不done不自合并。结果未到不能把协议/代码称执行成功。
