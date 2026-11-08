# R8.4：main64传输身份、J→P和协调恢复

Issue179 / Draft PR180；Melodydt。依赖R8.1/R8.2的原始main64入口与R8.3任务编译器。保留main原始225份锁源、P/U自身局控、U三源和独立TX保持槽、CF/J冻结控制子集与已有直接通路。stage.py只在生成副本的服务边界增加停止、排空和观测；不以旧generic LC替换main P/U。

## 硬件组成与停止边界

main64_recovery_top外层是持久主机/结果监督器，内部main64_recovery_engine包含主机装载、main母控（自带PM）、两个main局控和另外两个PM。共1MC/2LC/3PM/12程序bank；Block的私有S/T另计。执行ISA仍64位、单时钟、目标周期3.333333333ns。

服务入口halt后不再接受新的native服务，已接受的native命令与存储回执继续排空；其响应可由监督器清理，不再让被取消的LC继续执行。不能中途撤销已被数据宏接受的指令，不能因超时丢弃已对外提出的写请求。只有所有native、主机数据/片段和传输义务都排空后，才对完整内层组同步释放复位。SRAM数组不清零，复位撤销协议身份、镜像部署与有效位；新epoch必须完整重装、供数。

状态NORMAL→DRAIN→RESET（4周期）→WAIT_READY→FAILED/NORMAL。DRAIN_LIMIT默认1024；无法排空进入QUARANTINE，不复位、不丢未完成传输。消费失败终端后才能请求重试排空。主机回复背压与硬件排空区分：已排空但主机尚持有回复时等待，不把它当硬件超时。

## 传输、ACK和所有权

每方向一个main64_guarded_link，接受一字后保存128位数据和512位ticket。只有目的端真实SRAM写回执才记store_commit；请求ready不等于提交。正常ACK必须回显完整ticket；错ACK拒绝，源保持槽不释放。已发出的valid保持至接收，取消也不能撤回；尚未对外提出的字可以明确abort，abort不记提交。取消后仍提交的已接受写计入真实写字节和提交计数。

ticket各段按低位到高位列出；段内服务身份使用RTL拼接顺序{job,epoch,task_sequence,service_sequence,token}，token占最低3位：

| 位段 | 内容 |
| --- | --- |
| 130:0 | 源服务身份：job32、epoch32、task_sequence32、service_sequence32、token3 |
| 261:131 | 目的预约服务身份；P被动目的使用本次job/epoch和零任务/服务序号 |
| 293:262 / 325:294 | deployment generation / START sequence |
| 357:326 | 三端共同cohort topology |
| 389:358 / 421:390 | 源image ID / 目的image ID |
| 429:422 / 437:430 | 源Block ID / 目的Block ID |
| 447:438 / 479:448 / 489:480 | 目的S行地址 / J tag或零 / 字索引 |
| 511:490 | 保留零 |

U/U目的预约同时核对job、epoch、任务序号、服务序号和token。两端各计算一字→双向SEND→实际写入→RECEIVE→把接收字从S再次读出回送，核对两个方向的数值与真实ACK。固定两次传输/方向，服务序号步长3；不是任意路由网络。U/F/C→P保持P LC READY，源端完成全部提交后母控才CALL P；RAW128不建立数值格式兼容。

J→P使用已经由J提交的输出FIFO。桥检查job/epoch/task sequence、tag、index和last，把字复制入保持槽；正常输出消费与真实目的ACK绑定。最多4字，J源终端在整条路由完成前不交给母控，避免母控提前启动P。J输入片段租约和输出传输租约分开：JOIN/RELEASE结束本次T使用，已提交的FIFO/保持槽继续保存传输数据。取消时可清理本地FIFO副本，但已提出的远端写及保持槽义务仍须排空。

## 管理编码与编译入口

新schema safe64-native-tasks/1，target safe64/U/U等九配对；compiler.py/audit.py/host.py按schema分派。原main64、five、recovery语义保持。safe64_compiler.py生成三份执行镜像及transport_plan；safe64_audit.py独立构造完整字节和路线计划，不导入编译器/codec。safe64_host.py在PREPARE后配置路线，完整供数后DEPLOY。

op15为主机管理操作，不是64位执行opcode。低8位sub：
- 0：取消活动作业。15:8必须零，47:16 job、79:48 epoch、111:80 START sequence、143:112 generation，其余零，身份必须完全匹配。
- 1：请求协调复位。15:8为1..3的请求mask（仅诊断记录，实际复位整个组）；活动作业同上携带完整身份，空闲时身份必须零。
- 2：读取持久恢复状态，其余位零。
- 3：消费QUARANTINE失败终端后重试排空，其余位零。
- 4：路线配置。8为方向；18:9目的起始行；21:19字数0..4（0关闭）；53:22首服务序号；61:54服务步长；93:62 J tag；255:94零。只在NORMAL、未运行、未部署、无待消费结果或传输义务时接收。

U回送路线count2/stride3；U/F/C→P count1..4/stride1；J→P count1..4/stride0，服务序号是JOIN序号，ticket另含字索引。P不生成它不支持的RESERVE/RECEIVE，J不生成它不支持的SEND。独立审计验证实际软件路线和镜像同版绑定。

状态字沿用监督器格式：image_valid[2:0]、poison[5:3]、run_active[16]、pending[17]、result_available[18]、quarantine[19]、phase[22:20]、quiescent[23]、requested_mask[31:24]、epoch水位[63:32]、reason[79:64]及实时确认读/写/提交/ACK计数。状态/RESULT回复在背压下保持，失败终端跨内层复位保存并只消费一次；epoch水位不因内层复位降低。

取消结果status11；自动故障为0x200；排空超时为0x201。失败包[282]恢复标志、[283]隔离标志、[284]完整组复位策略；读/写是截至该快照已确认的计数，未释放的在途源读取不冒充已确认服务字节。失败包不承诺复原尚未生成的子级error_pc。普通母控RESULT写字节是LC服务累计；恢复实时ledger额外记录P被动写，不混为同一统计口径。

## 验证与边界

最终同版源码快照8a42dba：Slurm100544_0-8均在node1 COMPLETED/0:0；集成279/279（81正常、198故障/恢复执行）、结构9/9、链路单元21/21。服务器与本机逐项核验628份输入和797份原始产物SHA，31份当前仓库源码（含主机测试台）与实际运行逐字一致。最终新增软件检查1304/1304；R8.3软件1301/1301（在1299项基础上补2项Schema/目标登记对照）。元数据和文档在运行后补齐，不冒充RTL重跑。

功能测试台仍用10ns匹配银行功能模型；实现约束目标3.333333333ns没有改变，这些功能结果不证明新组合的300MHz时序。

run_safe64.py正常回放九配对×三程序×三初始化；故障模式覆盖精确取消、外来取消拒绝、外来服务返回身份、非法native描述符自动恢复、空闲请求mask与完整组复位、已接受目的写取消、外来ACK、排空超时隔离/重试、未提出字取消，以及双U反方向错generation ACK。每个恢复用例都重新装载不同epoch/地址/镜像/输入并正常完成，检查旧epoch拒绝、失败终端只消费一次、停止期间无新native接受。

run_link.py另以目的回执协议驱动器检查无所有权时的假ACK、未提出字abort、已经提出但ready为0的不可撤回写、已接受写等待真实回执、ACK背压和源数据保活；它是链路单元资格，不替代实际SRAM集成。structure.py执行全native lint、控制边界lint、Yosys通用结构综合和1MC/2LC/3PM/12bank计数；数据宏与银行为明确边界。

结果以work/Melodydt/179/control-r84-validation.json和当前PR实际回执为准，不把计划次数写成已通过。R8.5仍负责覆盖模型、更多周期交错和未覆盖闭环；R8.6重新冻结新顶层的综合输入/宏与存储器视图/SDC，随后组合映射STA、等价及后端。当前不宣称全部模型编译、完备故障覆盖或物理签核。

复现入口（只在授权服务器Slurm分配内仿真/综合）：

```bash
python3 -B project/control_task_compiler_v1/test_safe64.py --out software.json
python3.12 -B project/control_main64_recovery_v1/generate.py --check
python3.12 -B project/control_main64_recovery_v1/stage.py STAGE
python3.12 -B project/control_task_compiler_v1/run_safe64.py --stage STAGE --pair 0 --out RESULTS
python3.12 -B project/control_main64_recovery_v1/structure.py --stage STAGE --pair 0 --out STRUCTURE
python3.12 -B project/control_main64_recovery_v1/run_link.py --out LINK_UNIT
```


JSON形状与目标登记：../control_task_compiler_v1/safe64-schema.json、safe64-targets.json；形状检查不能替代编译器/独立审计的语义准入。
