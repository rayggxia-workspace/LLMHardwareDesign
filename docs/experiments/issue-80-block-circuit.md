# Issue80 阶段报告：完整宽控制器、有限暂存与局部连接

2026-10-25，UTC+08；负责人 Liangruizhi。[Issue80](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/80) / [PR81](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/81)，基于 PR77@889ca420181c932598c8e70c500dcdb01156b59c，独立 task/80-block-circuit / D:/Projects/LLMHardwareDesign-block-circuit。用户批准的首轮计划 1—3 已形成代码和实际证据，待审查合并；完整六 Block 子系统和目标物理宏尚未验收。

## 1. 已得到的结论

宽算术的反复读改写应优先通过有限的本地暂存和反馈连接实现。在同一套 8 条 S8/byte ALU、512B 单 1RW frame、单 ROM 以及相同程序/输入下，LOCAL 相比 BUS-frame 在最终 895 命令任务集减少 44.029% 的执行周期；外部取指按同一事务序号施加等待时仍减少 42.476%。四组完整 frame 逐位一致，算术动作、frame 请求和 ROM 请求数相同。

这补上了 Issue76 尚由软件承担的取指、宽算术控制、寻址和完成协议。它支持 V/S 局部反馈预连线候选，尚不能据此冻结 M/V 合宏或六类制造宏。这里的收益来自具体桥状态机的七拍开销减少，并非已测物理线长或整模型加速。

同一固定 Nangate45 研究库的逻辑映射中，LOCAL 面积多 38.304 µm²，约 0.157%；两侧完整 frame/ROM wrapper 均排除。它只是非制造研究库的逻辑面积估算，不能称为包含 SRAM/ROM、布线和时序的同面积 PPA。

## 2. 从参考项目落实到实际电路

[六模板规格](../BLOCK_CIRCUIT_SPEC_V1.md)列出 M/V/A/R/S/D 的计算、状态、接口、错误和预连线；[参考映射](../BLOCK_CIRCUIT_REFERENCES.md)定向核对 Gemmini、llaccel、openTPU，并借鉴 NVDLA、VTA 的组织。ref-project 未修改、未全面审计或重新 hash；报告中的核心片段、FP32 路径、多读复制存储及缺失数值依赖均保留来源边界。

新增 RTL 位于 project/rtl/wide_service：

|组成|实际实现及成本|
|---|---|
|byte_alu|8 条真实 S8×S8→S16 通路，加减/进位/位移/比较/mux；每 lane 3 输入/2 输出 byte 寄存，共 40B。单 context 每命令选一条，不能把总周期除以 8。|
|wide_engine|PC/边界、16B 两指令 cache、取指/译码、operand 读取、ALU 发射/返回、逐 byte RMW、4×32bit CALL/RET 栈、动态 shift 表选择、LUT 写回、watchdog、tag/status/done。host 不调度逐 byte 动作。|
|ram128|512B = 32×128bit，只有一请求口，读或写互斥；无 byte mask，部分修改需要读旧行再整行写。前 256B leaf scratch，后 256B 调用链持久变量。|
|lut32|单读端口 32768×32bit，131072B，其中原 LUT 有效 73736B；ROM 请求/应答及四 byte 写回由 RTL 执行，功能响应不代表工艺宏时序。|
|memory_link|128bit 半双工、一个在途事务、实际 header/data/响应状态及寄存；每读/写事务均 5 beats = 80B。不是免费 FIFO 或零成本抽象连接。|
|wide_block|BUS 候选的 frame 经过桥，LOCAL 候选直达同一个 frame；两侧取指和 CALL 表仍经过同一桥。busy 阻止 cfg 覆盖，完成保持到 ack。|

程序静态生成，不将输入值编成指令。原 807 case 逐项核验代码及原拓扑与输入无关；动态 shift 由运行时硬件读 selector 选择有限地址表，不能由 host 逐输出选程序。最终程序 241104 个 64bit word，1,928,832B，明确占 EXT 128MiB 预算中的程序 32MiB 配额，cache 仅 16B。不能把约 1.93MB 程序当成免费内部 ROM。

程序镜像为 120552 条 16B 行，单纯以 16B/拍装载的带宽下界为 120552 拍，尚未计协议、介质或软件装载时间；本批是预装后运行，部署成本另列，不反复摊成每个命令都下载一遍。调用者实际每命令写 32 行/64 边沿、读 32 行/64 边沿，完成保持与 ack 4 边沿，均单列计量。

## 3. 独立数值、协议和公平性

所有真实数据提取、RTL、综合和独立接收仅在 /public/home/yuzelu/RuizhiLiang/issue80-block-circuit-20261025 的 CPU Slurm 作业 lrz-i80-* 执行。Verilator 5.042；Yosys 0.63，git70a11c6bf；既有只读 SIF c742bf99ea498fb4da5135bc83fd1677abcebe0e64470e6a115f2baecb3905df；没有新模型或软件安装。PC 只有源码、微小合成和 JSON/字节接收。

|组别|每配置数目|覆盖范围|
|---|---:|---|
|原 typed 宽算术|807|18 函数、132 真实 Granite 标量码、原有限 shift 域、INT32/64/128、RNE/溢出旗标/零除；原数学语义不变。|
|真实 ROM|69|实际 ROM 字节和请求地址，非 host 直接填结果。|
|协议负例|7|非法编码、RET 下溢、guard、shift129 超域、ROM 超域、栈溢出、PC 超域。|
|RQ 消费者链|4|硬件乘法→动态 scale 译码→RNE，含 130/131 大移位和负 shift 拒绝。|
|八专家 merge 链|6|两层、评价 token0/64/71、坐标0，八路实际 down/gate→一次 RNE→原输出比例→原 residual；不冒充完整 1536 hidden norm。|
|完整缩小 RMSNorm|2|8 元素平方和、除法、epsilon、开方、gamma 和逐元素 RNE；合成输入，非整模型质量。|

最终两组织×两等待环境 = 3580 个命令，均独立通过。每配置另外实际到达 REQ/WAIT_R/RMW/TABLE/ROM_WAIT 五个活动状态再 reset，确认 20 个边沿无旧完成且未触碰 SRAM marker 保留；busy cfg、请求背压稳定、tag/status/done 保持亦有实际断言。私有 scratch 在异常前可能变化，这不等于 R 的双代状态原子发布已实现。

独立 verify.py 不导入 compiler 或 micro.py，使用另一套 bigint/RNE 数学核。每组实际改写一个接收结果、重新保存及计算 SHA 后仍被拒绝；面积接收也有两份改写标签且重 SHA 后拒绝的负例。文件完整性和数学正确性分开验收。

正式 03 的等待按外部事务编号决定：第 n 个请求等待 n mod3，接收后响应延迟 1+(n+1)mod5；不引入 RNG。两侧外部取指序列相同，故等待相同。早期 01/02 按全局时钟相位决定等待，虽然数值合格，性能不列正式排名，原结果保留。冻结协议的“固定种子”在实际最终实现中细化为上述确定的事务序号规则，不从有利样本事后挑选。

## 4. 实测周期和资源

|最终环境|BUS 执行 cycles|LOCAL 执行 cycles|减少|含实测 caller IO/完成的 BUS 边沿|LOCAL 边沿|
|---|---:|---:|---:|---:|---:|
|无额外外存等待|69215400|38740445|44.029%|69334435|38859480|
|同外部事务等待|71746249|41271294|42.476%|71865284|41390329|

两环境均精确少 30474955 cycles = 7×4353565 次 frame 事务，少 21767825 wire beats = 348285200B。frame 读取 3080018、写回 1273547，算术动作 1679162，指令 cache 行读取 842566，ROM 69。取指＋CALL 表的外部事务在两侧均为 843617；BUS 另带 frame 后总事务 5197182。完整请求/响应入账，不只比较 payload。

|静默环境子任务|数目|BUS cycles|LOCAL cycles|
|---|---:|---:|---:|
|原宽算术|807|44793258|25127654|
|ROM|69|9660|4830|
|协议负例|7|565|376|
|动态 RQ 链|4|391955|222709|
|八专家单坐标 merge 链|6|3175998|1810074|
|8 元素 norm 链|2|20843964|11574802|

任务集分布不是模型算子频率。尤其 norm8 平均 LOCAL 5787401 cycles，说明纯 byte lowering 的绝对代价仍很高；约 44% 的组织收益不能掩盖这个问题。后续需比较有限宽算术/RF/SFU 专用化，并把多周期、面积、ROM/端口和精度成本全部计入。

|库存/综合指标|BUS|LOCAL|边界|
|---|---:|---:|---|
|S8×S8→S16 实际乘法器|8|8|wreduce 后逐实例宽度核验，无原生宽 div/mod/pow。|
|frame / ROM / 返回栈位数合计|1052800|1052800|4096 +1048576 +128；不是已映射 SRAM/ROM 宏。|
|不含 memory cell 的寄存位|2138|2138|包含实际控制、桥、数据通路和 debug counter；40B operand 不另重复相加。|
|generic leaf cells|910|915|通用操作单元计数不是面积。|
|参考库实际逻辑 cells|16212|16222|2001 个 DFF_X1 两侧相同；3 个 scope 注释不算硬件。|
|参考库逻辑面积 µm²|24374.112|24412.416|共同 frame/ROM 整体 wrapper 排除，局部增加 0.15715%。|

通用 memory 的 frame/栈表现为读 array 加注册 wrapper，运行接口控制为单 1RW；不能直接称已完成商业同步 SRAM 宏映射。逻辑库来自官方 OpenROAD-flow-scripts@cca3a717920067d8f6e085ce886fe4ecdc876614 的 unmodified NangateOpenCellLibrary_typical.lib，SHA256 8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1。其 README 明确为非制造研究模型；保留 LICENSE/来源，不使用 fakeram 冒充真实 SRAM。接收独立核对实际网表实例、原库 area 与 Yosys 原生 stat，非只接受脚本面积字段。无 mapped-gate 功能等价、目标 STA、RC、布线/CTS 或功耗验收。

## 5. 对 Block 边界的影响

1. 制造前优先保留 V/S 的有限局部 frame、RMW 反馈、单口仲裁、宽运算控制和受控 ROM 服务；这是完整电路证据支持的第一处局部预连线。具体 frame 的容量、宏形态和 bank 数仍需真实工作行/队列与宏视图验证。
2. M 保留同单位 INT32 fullK 局部累加、完整/partial 标签及可绕过的 RQ/宽对齐出口。Issue76 近 M 位置差很小，而本轮高收益来自共同 microframe 组织，因此不能把 44% 写成 M/V 融合收益。
3. A/R 仍保留完整统计/归约、连续状态、unit/owner/epoch/guard 与原子发布义务。本轮只落实可复用 V/S/D 底座，未实现 GDN/Mamba 的完整状态机，不能把五类 reset 测试当作 R rollback 验收。
4. 动态 expert dispatch、M/V/A/R 间旁路、bank/backing 的产品端点以及物理相邻关系继续留给后续定制；六逻辑模板不强制对应六个硬宏。与成员 Issue55/63/PR79 对接，不复制另一套完整底座或通信 adapter；packet 合同和冻结层字段须先统一。

[Block v2 第15节](../BLOCK_PARTITION_V2.md)及[决策记录](../decisions/2026-10-25-local-frame-and-wide-controller.md)保存上述取舍。下一阶段最小集是有真实 M partial 的完整消费者、受限宽算术/SFU 专用化的同精度成本对照、明确宏和 PVT/端口后的局部布局时序。不能跳过实现资格直接宣布最终物理边界完成。

## 6. 可接收的证据和未完成项

[索引](../../project/experiments/block_circuit/results/issue-80/index.json)记录 600 个成员和每个 SHA；完整包保留所有八个源码 phase、输入/程序/ROM、实际输出/编译/综合、原失败与语义负例，留授权服务器 delivery01/full-results.zip。118979927B，SHA256 368c06b6d779ce55d322d9f5b405944e15a21019292b64ab8eba7356d01b6b32。精选 metadata 708937B /271成员，SHA256 c9448a6ebc539713dd4507b29f2726b02245de8f5b988502d52db4f6a1281dcc，已入仓库。

服务器对完整包、精选包逐成员核验 PASS，PC 对精选字节和八 phase 的 123 份原 Git blob 核验 PASS。archive 快照后的归档/接收作业终态、命令和回执另在 work80/execution.json / slurm-final.json，不能假称其自身运行日志已经包含在之前的 archive 中。源码 phase5 是最终数值批，phase4 是 generic，phase7 是逻辑映射；整理源快照 phase8 commit 为 8f95edc5271719a594ae0a4c6c3b5b00248f30a1，文档交付 commit 以 PR head 为准。

共 48 个本人作业，45 COMPLETED /3 FAILED：90449 为编译器误用非 shift 算子原记录无关 shift，修正只选择 selector0，保留原参数/数学/失败；90489/90490 为逻辑面积接收把 Yosys scope 注释当未映射单元，修正显式区分注释后 90491/90492 重新通过。两次早期缺 ROM 的 pilot 有 warning，仅列诊断，不算 ROM/完整数值验收。没有中断他人作业，没有覆盖旧结果。

16 个新合成边界/接收检查、69 个相关既有测试、管理结构检查通过；完整仿真/数学/协议/面积接收另有独立服务器收据。登记仍为 management-hub PR5 pending；board.json 404，实际 Projects 查询报 INSUFFICIENT_SCOPES（缺 read:project），条目未核，看板 unverified、同步 pending，管理员及审查人待指定。Issue80 交付后 in_review，不 done、不自行合并。正式宏/STA、完整 M/A/R 子系统和整模型质量不属于本轮已完成项。
