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
L_OPEN/RX/TX/MOVI/REPORT/DROP、算术/循环/分支、RX-close和完整provider协同复位均未实现；部分闭锁端口仍为0。第8步已支持匹配身份的CANCEL与128周期排空期限，详见下节；未支持的服务仍由能力profile限制。
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
