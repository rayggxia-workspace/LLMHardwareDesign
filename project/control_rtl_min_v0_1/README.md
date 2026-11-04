# 最小功能局控 RTL v0.1

Issue179／Draft PR180，第7步。继承PR176的五类Block研究和第6步92信号边界；本切片仅面向P类型中的空任务与M clear控制，不实现完整P Block或母控RTL。

## 实现与程序范围

- `lc_min_controller.sv` 是功能DUT，外接8320B程序存储器、M服务适配器、整包传输和cohort协调器。
- 支持配置BEGIN／WRITE16／READ16／VERIFY_PASS／PREPARE／ABORT；完整实际读回后才验证，局部PREPARE后仍须匹配外部deploy。
- CALL接收64B包，读取完整64B任务描述符，再以PC读取16B指令。支持L_EXEC／L_WAIT／L_END；1个在途服务、8选1 token编号、单IREG／无预取。
- EXEC读取128B执行描述符；仅接受既有ABI65537下M clear服务的参数组合。native_abi_id位于该记录字节56，ISA与已装配镜像不改。
- 单128bit PM口由配置、取指、描述符读取互斥使用；请求／响应各自握手，响应与补发有空拍。WAIT不能在完成响应同拍退休；终态包保持到母控整包接受。
- 配置候选内错误使候选失效；错误BEGIN在切换前拒绝并保留旧提交。空闲撤销部署回INVALID，运行中失去许可置POISONED。
- 本地reset清除准入。release证书的新鲜性跨reset由外部协调器保证，LC不保存抗回放非易失状态；local reset不证明provider复位。

此为可执行的严格子集：头部限1任务、0对象、0transfer／event binding、0或1执行描述符、最多256指令；任务类型P、参数/对象mask为0；任务序号须在本次release后递增。它不代表全部ISA v0.1程序都可运行。
算术/循环/分支、RX-close和完整provider协同复位均未实现；部分闭锁端口仍为0。第8步已支持匹配身份的CANCEL与128周期排空期限，详见下节；未支持的服务仍由能力profile限制。
身份不符的服务响应ready为0，外部适配器须隔离这类响应；本切片未证明无tag原生宏的迟到响应安全。

## 验证方式与证据

`wiring.py`从第6步contract.json生成同名同宽的平铺端口、testbench接线和92信号采样打包；Icarus的interface支持限制不改变逻辑边界。生成器不生成DUT状态转移或预期输出。
`tb_lc_min.sv`提供实际读写的有限PM、M clear服务响应peer和背压；程序全部经过配置口装载，没有层次引用注入DUT内部寄存器。
`run.py`调用真实HDL编译/仿真，解码DUT采样，再使用未修改的第6步check_cycles.py检查五份执行轨迹，并独立检查退休操作码序列。五个负向配置／部署场景由testbench断言检查，不冒称通过只支持标称轨迹的旧checker。

```bash
python3 -B project/control_rtl_min_v0_1/wiring.py
python3 -B project/control_rtl_min_v0_1/run.py --simulator verilator --verilator /eda/verilator-5.042/bin/verilator --out /work/results
```

Verilator需可用的C++20编译环境及4个构建线程；服务器使用现有ORFS 26Q1容器，G++11.4／Python3.10.12，宿主直接执行的Verilator因GLIBC不兼容不可用。
可选Icarus入口为`--simulator iverilog --iverilog <path> --vvp <path>`，本轮Windows Icarus进程异常退出，不能将该入口描述为已验证。

最终[实际报告](run_report.json)、[验证与作业索引](../../work/Melodydt/179/control-min-validation.json)记录源码SHA、输入镜像SHA、工具版本、输出与日志SHA。
旧checker返回的`rtl_tested:false`表示它自身不认证输入来源；实际HDL调用由外层`actual_rtl_simulation`、命令、作业日志及源码摘要作证，没有改写旧checker返回值。

这是Verilator功能仿真，尚无四态仿真、综合、形式证明、频率／面积／功耗或M11/M12物理证据。M服务是行为peer，未实例化真实M宏、S或完整Block；母控也是外部peer。
下一步先增加取消／异常排空及服务适配器验证，再扩RAW16与RX/TX；真实provider接入和五类控制profile仍待后续。

## 第8步：取消与有界排空

保持既有ISA和92信号边界。匹配CANCEL在RUNNING/CANCELLING接收，无需新的终态信用。取消停止新请求，但此前valid遭背压的请求必须保持到接单；其实际PM／服务响应到达后才能清理令牌并返回ERROR11。native错误优先；重复CANCEL不重置排空计时、不重复返回；已经锁存的终态不改写。
DRAIN_LIMIT默认128周期，0表示关闭期限；到期仅置POISONED并保留未闭合任务／服务／返回预约，不虚构终态。静默／复位证书和完整provider恢复仍为外部合同，不能靠软件tag证明无tag宏旧响应安全。

```bash
python3 -B project/control_rtl_min_v0_1/run_cancel.py --verilator /eda/verilator-5.042/bin/verilator --out /work/results/cancel
```

[取消实际报告](cancel_report.json)记录22场景／18719采样边沿、19安全结束／3隔离，6项观察轨迹破坏检查均拒绝。全部测试及旧173检查／10原RTL在服务器执行。新cancel_check.py继承未修改的边界checker，并补全CANCEL native错误终态丢弃IREG的架构点；它不修复或生成输入轨迹。原run_report.json保留第7步历史，当前10例重跑回执在work/Melodydt/179/control-cancel-validation.json。

## 第9步：故障与有界等待

CALL在握手前检查身份；错误目标／镜像／epoch／序号拒绝且不产生关联终态。EXEC资源不支持返回4，字段非法2，描述符非法5；运行非法指令1、状态7、PM10、max_steps12均测试。已接单服务必须真实排空，native错误优先；ERROR锁存并保持整包。
STALL_LIMIT默认128，连续无实际PM／服务握手进展且存在未完成义务时POISONED；不针对终态背压，不假造终态／退还信用。DRAIN_LIMIT仍用于CANCEL。两个参数为0分别禁用对应期限；目前只测试默认128。
[fault_report.json](fault_report.json)为实际29场景；旧run_report与cancel_report分别保留第7／8步历史。本次当前DUT的10原／22取消重跑摘要及SHA在work/Melodydt/179/control-fault-validation.json。所有仿真在服务器。fault_check.py检查原始采样，不生成或修复信号；旧checker保持不变。六个故障轨迹突变均拒绝。
复位测试范围仅控制器＋有限PM／M peer；RAM保留但需新release与完整装载／读回／部署，新epoch任务才可运行。真实宏和cohort协调器未接入，R3整体尚未完成。

## 第10步：严格M clear服务适配器

lc_m_clear_adapter.sv绑定当前描述符与现有block_v2_m原生cmd6／index0／data0；独占M、无外部读者的clear-only子集。保存任务身份、拒绝非法资源／描述符、持有原生命令／返回直到接受，真实native响应后才返回服务完成。窗口外无tag响应或provider许可撤销poison，不撤回已保持命令。provider_released是外部复位／隔离前置条件，尚无cohort协调器。
adapter_report.json区分10协议peer负向场景和5现有M RTL连接场景，5真实命令／5响应及3错误轨迹突变拒绝；M源blob d91ffdf904bc77c19d5d0ecfd4cd11560b44a417未改。所有仿真在服务器；完整命令、75源码／76日志SHA和作业97223／97224见control-adapter-validation.json。未验收MAC数值、共享context、其他服务、S、完整Block或物理。

## 第11步：单RAW16逻辑对象

L_OPEN／DROP读取64B对象描述符，限定静态16B、版本1、槽0、16KiB范围；不产生S有效数据。正常结束要求对象与服务均释放；CANCEL先真实服务完成／令牌清理，再对象清理，最后终态；POISONED保留未完成义务。新增L_MOVI及8×32bit寄存器声明，目前只验证指令退休／错误寄存器拒绝，值读回待L_REPORT后补证。
执行与对象描述符均使用显式loaded位，避免全零非法记录重复读取。object_report.json为实际27例／3轨迹突变；79输入源码与103当前场景日志SHA见control-object-validation.json。97225跑全旧回归＋26对象，97226只改runner增全零执行记录，DUT／其余仿真源完全一致。单对象缓存64B和寄存器声明32B非综合成本；没有真实S、收发、完整Block／母控／物理资格。

## 第12步：受限P RAW16收发

L_RX／TX读取64B描述符并绑定研究路线host255→0／0→1，支持单静态RAW16对象、单服务、16KiB范围。RX在有限peer实际写SRAM／发送ACK后完成；WAIT消费成功令牌才标对象valid；TX须声明输出并valid，源收到peer存后ACK才完成。L_REPORT仅READY，实际读MOVI寄存器并保持整包；已知服务错误后不新发READY，锁存包保持到接受。锁存READY期间CANCEL保持不接单，先消费包再接单排空；返回消费者不得因此阻塞。
transfer_report.json的25场景及4错误轨迹覆盖R0／R7／32bit高值／未写R0初值、连续任务新payload、末字、权限4／状态7、传输字段／路线／全零记录、写错／ACK后错误前缀、CANCEL和2隔离。control-transfer-validation.json关联84源码、128当前RTL场景／8编译日志SHA与3作业。97227旧回归通过但新TB编译失败，最终97229新场景通过，源码SHA关联有效；旧报告保持历史。
R3首个受限P控制门满足，下一步R4母控；通用ISA／其他服务、原生S、flit串行化、RX-close／真实cohort及完整Block仍待。本步存储／ACK为有限行为peer，不转移原生S或物理资格。

## 第13步：母控协议RTL（R4进行中）

mc_min_controller.sv＋mc_ports.svh／mc_pins.json为81信号2722位母控边界。单4736B PM、128bit指令／单IREG、最多256条、2目标／8完成token，支持G_CALL／WAIT／EVENT／MOVI／END。START参数区本profile为0，寄存器清零；G_PARAM未实现。每端一个READY＋一个终态槽，CALL预留信用后锁存整包；返回独立推进。首错停止新工作、保留offered CALL／PM、匹配CANCEL并实际排空；缺终态／坏返回／撤销部署隔离保留所有权。主机结果完整身份／首错PC／确认前缀饱和／溢出字段保持。
tb_mc_min.sv只有实际母控及两个有限子协议peer，不含LC；mc_check.py独立重建PM／寄存器／信用／PC，run_mother.py在服务器编译运行。mother_report.json记录26场景（22执行／4准入负向）和4错误轨迹拒绝。control-mother-validation.json区分五次作业，最终97234 COMPLETED0:0；旧173软件／128局控RTL源码未变，证据沿用，不冒称重新运行。R4下一门为实际两个LC RTL＋有限SRAM／链路；不是完整Block／原生S／物理或一般死锁自由证明。

## 第14步：实际母控＋两个局控（R4有界门）

tb_control_network.sv实际接mc_min_controller＋2×lc_min_controller，tb_network_local／pm提供有限PM／16KiB SRAM／单服务；每端一个RX arm、一个TX payload和ACK状态。先消费者READY再生产者，逐级真实写存／ACK才完成；全包与信用跨端逐周期相等，network_check.py＋既有独立母／局checker交叉核对。实例MC/LC STALL4096、LC DRAIN128，DUT源码未改。
network_report.json记录10集成／4突变拒绝：连续job、R7高scalar、返回背压／CALL独立回收、READY前错误、恢复后端点task_sequence不同、缺TX ACK／错误时RX不能关闭的隔离。原生S／flit串行化／RX-close／真实provider复位／完整Block未实现。control-network-validation.json列106源与61日志／4编译SHA、3作业；97243最终0:0，25局控重跑，26母控复用97238已通过且源不变。transfer_check新增显式每job输入版本／错误预期与取消保留IREG；默认旧场景不变并已回归。下一步R5。
