# 母控／局控第1步：控制接口、原生服务与资源合同 v0.1

2026-11-04 17:39，Asia/Shanghai（UTC+08:00）。负责人 Melodydt；[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)。代码父提交 df3e7a2657a96bf0e5031a958d48155010bd7380；设计上游 PR176 固定为 08f2ea20a11dfdd09892a67599163e32b7237edb。

本轮执行“建立控制接口与资源清单”。母控／局控的架构和协议为研究对象；完整 Block、计算宏、S 扩容、模型数值和系统物理由外部实施任务负责。[总方案](TWO_LEVEL_CONTROL_PLAN.md)、[ISA v0.1](CONTROL_ISA_V0_1.md)保持原范围。**本轮建立来源绑定和字段合同，不实现控制器或 Block RTL，不执行指令或数值计算。**

## 1. PR176 的同步规则和本轮检查

按用户要求，每次开始／恢复研究及上传前，读取 PR176 的 head、状态、说明、顶层评论、review 与逐行评论。发生变化时先比较差异，再同步受影响的资源清单、数值／接口假设、程序／拓扑合同和来源版本；已有版本和失败记录保留。控制合同不得一部分绑定新设计、一部分仍无说明地沿用旧设计。

本轮开始检查结果：PR176 head 仍为 08f2ea20，无新增提交，评论／review／逐行评论均为空；未改 PR176 分支，也无需要移植的上游变化。发布前另行检查并记录于[同步回执](../../work/Melodydt/179/pr176-sync.json)。这是每次研究的人工触发工作流，未配置后台定时监测。

若上游 head 改变，先读取相关 diff 和设计材料，在本任务分支正常同步／修订；不能强推或替换其他人的工作。若上游已合并，先核对 PR base 与累计差异再调整。受影响字段尚未澄清时明确列待确认项，其余控制研究仍可推进。

## 2. 已完成的交付与证据层次

| 产物 | 数量／作用 | 当前性质 |
|---|---|---|
| native_interfaces.json | 6 个实际模块、149 个端口声明及来源／握手／复位语义 | 从固定 RTL 读取；不是新实现 |
| control_links.json | 母控↔局控消息、局控↔适配器元数据和完成强度 | 控制接口建议，不是原生宏已有 pin |
| services.json | 12 个 P 范围服务；native 字与原生字段的拟议映射 | 可静态检查的控制 ABI 提案；适配 RTL 未实现 |
| profiles.json | 五类型资源目录，2 个 P16KiB 控制研究 profile | 数据端点需求清单，不是已连通版图 |
| contract.py / examples.json | 字段／对象窗口／路线检查及 5 个示例 | 只做静态检查，始终返回 deployable=false |
| test_contract.py | 15 组独立端口值／字地址／拒绝测试 | 不替代指令执行、宏数值或 RTL 验证 |

正式文件位于 [project/control_contract_v0_1](../../project/control_contract_v0_1/README.md)。[来源索引](../../work/Melodydt/179/control-interface-sources.json)包含固定 commit、Git blob 和 SHA-256；[实际验证](../../work/Melodydt/179/control-interface-validation.json)记录本轮命令与产物。

## 3. 母控与局控的控制合同

沿用 ISA 的 64B task_message／event_message；候选命令／返回各32bit，一包16个有效 flit，包内不交织，背压保持。链路 pin、网络形状和队列深度尚未冻结。

| 边界 | 接受点 | 完成或退休点 |
|---|---|---|
| 母控发送 CALL | 整包被接受，局控有任务槽且最终返回空间已预约 | 接单不是任务完成；G_WAIT 消费匹配 DONE／ERROR |
| 局控接收 CALL | 核对 Block／job／epoch／task_sequence／image／topology 和常驻 task_descriptor | 由本地 task.entry_pc 取指；CALL 不携带整段程序 |
| 局控报告 READY／PROGRESS | 整包被接收，事件槽按绑定和当前任务核对 | 母控消费事件后释放槽；背压不得覆盖旧事件 |
| 局控返回 TASK_DONE／ERROR | 终态 tuple 一次锁存，保持至接受 | 母控匹配完成令牌及任务身份后退休，防重复／旧事件 |
| 局控启动宏适配服务 | 字段／资源／锁／容量满足且请求真正接受 | 按注册完成类别产生局部令牌结果；不能按 busy 推定完成 |

适配器须保存服务序号、局部令牌、任务／上下文身份和输入快照。M/G/S 的原生接口没有 job／epoch／服务序号字段，这些关联由控制适配层持有；对无 tag provider 采用同任务域排空／协调复位，不能仅凭更换 epoch 假定无限迟到响应安全。G_WAIT／L_WAIT 不停止宏响应、S helper、收发或控制返回。

## 4. P 范围的实际原生端口

### 4.1 M：命令／响应及独立 A/B 装载

| 方向 | 字段 | 含义 |
|---|---|---|
| 局控适配器→M | cmd_valid、cmd_op[3:0]、cmd_index[5:0]、cmd_data[63:0] | 在 cmd_ready 时接受命令 |
| M→局控适配器 | rsp_valid、rsp_data[127:0]、rsp_error、rsp_saturated | 在 rsp_ready 时消费响应，必须保持身份关联 |
| feeder→M | A128：bank／row／tile／wide；B512：bank／tile／wide／half | 分别按 a_valid&&a_ready、b_valid&&b_ready 接受 |
| M→控制层 | busy | RTL 中是 !cmd_ready，不能当作结果上下文是否空闲 |

正常命令接受为非复位时 cmd_valid&&cmd_ready；完成以匹配 rsp_valid&&rsp_ready 为准。原 RTL 允许旧响应消费与新命令接受同拍，适配层必须先关联旧响应，再更新新命令身份。

M 有两份操作数 bank，但只有一个完整结果上下文。GEMM 响应后结果仍可被后续追加或读出；读出不释放结果。op11 只使选中操作数 bank 失效，不清结果；op6 清操作数／结果／partial 有效位，但不复位 scale。逻辑 owner 释放必须在响应及全部读／消费者义务结束后完成。

GEMM 的 rsp_data 低8bit为 fault_rows，rsp_error表示至少一行失败；成功行仍可能提交，不能把错误响应解释成整条命令没有副作用。控制层必须保留确认／错误范围并按合同处理。

### 4.2 G：两路 S16 流式流水线

原生输入为 in_valid／in_ready、in_fn[2:0]、in_gated、in_x[31:0]、in_gate[31:0]；输出为 out_valid／out_ready、out_data[31:0]、out_error／out_saturated。**G 没有 cmd_op、busy 或整段 done pin。**

每次输入握手接受两个 S16 元素，输出按序匹配；四级流水在输出背压时整体冻结。有限服务必须计数输入／输出包并处理写 S 的确认，不能用“经过固定4拍”判断服务完成。

in_fn=0/1/2/3 对应 SiLU／Sigmoid／GELU_tanh／Softplus。输入和 gate 为 Q5.10；未门乘 Sigmoid 输出 Q1.14，其余及门乘结果按既有合同解释。对象的 S16/S32 容器编码本身不证明 Q 格式兼容，完整程序的类型／尺度传播仍待后续编译检查。

### 4.3 私有 S 与 feeder

私有 S 使用 PR178 的固定包装：CLIENTS=4、WITH_FEEDER=1，16KiB、4 bank。P 客户编号为0=M结果／访问helper、1=G helper、2=RX、3=TX；不是另外增加一个局控裸 RAM 端口。

req_valid[client]&&req_ready[client] 只预约命令寄存器。仲裁器保存 wr、10bit字地址、128bit数据和 owner，再访问真实存储，最后仅把响应交给该 owner。写确认必须等待 rsp_valid[owner]&&rsp_ready[owner]；源请求接单不是 stored ACK。一个客户拒收返回可阻塞本块普通口，不能据此推断其他 Block 也被阻塞。

普通地址单位为16B，范围0..1023；wide地址单位为64B。feeder 的 load_a_base／load_b_base 仍是16B字地址，必须4字对齐。输入 rows1..8、tiles1..4，控制 bank／Awide／Bwide／reuseB。接受为 load_valid&&load_ready，完成为 done_valid&&done_take 并读取 done_error。busy=0 时完成消息仍可等待消费。

feeder A 源长度为 tiles×(rows>4?128:64)B，B 源长度为 tiles×(Bwide?128:64)B；reuseB 不读 B，但必须已有同 bank／格式／几何的 B。完成只证明有限 A/B 装载退休，不证明 M 计算完成。

## 5. 12 个服务的 native 字映射

proposed native_abi_id=65537（0x00010001），仅为本研究局部提案，不能当作已部署硬件 ABI。ISA opcode／execution 记录布局保持 v0.1。未登记的 ABI／resource／service／native_op 一律拒绝。

原codec的两个程序骨架不因此成为本native ABI的可执行程序；后续必须显式生成匹配的描述符和版本，不能自动兼容旧二进制或旧ID。

M 的统一映射为 native0=cmd_index（仅低6bit），native1=cmd_data低32bit，native2=cmd_data高32bit，native3..7=0。

| 注册名 | resource/service/native_op | 静态字段 | 完成类别 |
|---|---|---|---|
| M_READ_S64 | 0/2/3 | index=row×8+pair，row0..7、pair0..3；data=0；一次128bit响应 | LOCAL_STORED |
| M_CFG_SCALE | 0/0/4 | index0；data[15:0]有符号系数、[20:16]左移；其余0 | NATIVE_DONE |
| M_READ_RNE | 0/2/5 | index=row×8+half，half0..1；data[5:0]右移、[9:8]宽度0/1/2，[7:6]及高位0 | LOCAL_STORED |
| M_CLEAR_ALL_VALID | 0/0/6 | index0、data0 | NATIVE_DONE |
| M_GEMM | 0/0/10 | index[5] bank，低5bit0；data[0:2] Awide/Bwide/clear，[3]=0，[7:4]末K，[11:8]N，[14:12]tiles，[18:15]rows，高位0 | NATIVE_DONE |
| M_CLEAR_OPERAND_BANK | 0/0/11 | index0..1、data0 | NATIVE_DONE |
| M_READ_PARTIAL | 0/2/12 | index低3bit<4、data0；partial有效与bank_owner必须运行时匹配 | LOCAL_STORED |
| G_SILU／G_SIGMOID／G_GELU_TANH／G_SOFTPLUS | 3/3/0..3 | native_op直接给in_fn；native0 bit0=in_gated，其余native字0 | LOCAL_STORED |
| S_M_FEED | 5/1/0 | native0=bank、1=rows、2=tiles、3 bit0/1/2=Awide/Bwide/reuseB；4..7=0 | NATIVE_DONE |

M GEMM 几何为末K1..8、N1..8、tiles1..4、rows1..8；A/B是否真正装好和追加结果是否同owner必须后续运行时核验。feeder 的 native_op0 是控制 ABI 选择值，原 feeder 没有 opcode pin。

M NATIVE_CMD 不使用对象流，count／stride为0。M_READOUT 为count1、stride16，将一份128bit响应存入dst，再等真实S client0写响应；op3/12 dst为RAW_BYTES，op5可为RAW_BYTES或四个S32容器。M op5的每个S8/S16结果仍占一个32bit输出容器，不是紧凑S16数组。

G 的首个参考服务用 S32 存储容器承载 S16有效值：一个128bit S字拆成两个原生G包，输出再符号扩展为四个S32容器写回。count按原生双元素包计，必须是2..2048的偶数，stride8；src0、可选src1和dst为不同对象，整16B窗口，无隐含尾字写掩码。Q格式和源S32高16bit为符号扩展是编译／运行前置条件，字段检查器尚不验证数据值。

这些装拆／holding／S helper 为待实现的适配需求，不是本分支新增Block RTL；原生G仍为两路S16。M→G直接流水、紧凑S16读出、DRAINED服务及N/E/R/T/MEM原生注册均未在此子集中登记。

## 6. 资源和拓扑 profile

| profile | 固定控制归属／资源 | 声明的数据路线需求 | 字段检查行为 |
|---|---|---|---|
| P16_M_ONLY | M/G/S各1，mask0x29，S16KiB／4 bank／4客户，1活动任务、8令牌、16对象、M context0 | feeder→M A/B；M响应→S client0 | 允许已登记M与feeder；G虽可控，但缺数据路线，拒绝G执行 |
| P16_VIA_S | 与上行相同 | 另有S client1↔G容器适配需求 | 增加已登记G服务；M/S/G通过S对象衔接，仍须类型／生存期检查 |

这两份 profile 是供后续模型使用的端点需求，不是物理连通证明；同一个资源mask不等于同一个数据可达性。完整程序及真实接入仍需显式对象布局、ABI／拓扑ID及输入完成条件。

五类目录保留 P=M/G/S、U=N/E/S、C=R/G/E/S、F=G/E/S、J=E/S/T。P32KiB为PR176候选，不继承本16KiB研究合同；其他类型的原生服务注册为待执行，不能因为目录里有某宏就接受其L_EXEC。

## 7. 静态检查器的范围与实际结果

检查器复用现有 codec 的128B execution／64B object字段规则，检查 ABI／服务、native位、L_EXEC资源和描述符索引、完成类别、静态对象容量／对齐／重叠、窗口与路线。首个子集只允许 context0、静态地址和无参数provider；动态寄存器引用、原地G对象和未登记服务拒绝。

输出 static_fields_valid=true 只证明所覆盖的字段检查通过，deployable 始终false，并列出未完成的上下文、有效性、Q格式、源内容、运行时身份和真实ACK条件。它不执行PC／循环／令牌状态机，不是R2二进制解释器或完整镜像检查器。

15组测试覆盖全部12注册项、手工M端口值、字节→16B字地址、B复用前置条件、同控制mask／不同数据图、保留位、G整字分组、对象容量／别名／动态字段、完成强度及L_EXEC身份拒绝。首次开发测试发现生成的注册JSON未同步以及预期异常文案不符，均修正后完整重跑；没有改动原生RTL或放宽非法字段检查。

```powershell
python -X utf8 -B scripts/check_project.py
python -X utf8 -B -m unittest discover -s project/control_isa_v0_1 -p test_codec.py -v
python -X utf8 -B -m unittest discover -s project/control_contract_v0_1 -p test_contract.py -v
python -X utf8 -B project/control_contract_v0_1/contract.py examples
```

实际命令／版本／结果与SHA在本轮回执记录。没有服务器作业、RTL仿真、模型计算或物理实验，没有自动监测。

## 8. 下一步与待确认项

本轮完成第1步的P范围接口基线；R1整体还包含镜像／装载准入和更多服务合同，尚未完成。下一步先基于本注册表写空任务、单M命令和有界G／feeder任务的预期控制轨迹，再定义完整镜像装配与配置装载。

后续模型须补齐：逐服务序号／令牌生命周期、M操作数与结果上下文、对象有效字节／尺度类型传播、G有限holding／分组、真实写ACK、取消和无tag provider排空／复位，以及可检验的进展假设。任何外部Block实现接入前先对实际端口／源码版本和有限资源重新匹配；本轮静态测试不转移系统资格。
