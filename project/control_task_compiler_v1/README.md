# 第7步：统一受限原生任务编译

Issue179 / PR180；Melodydt。入口是`bounded-native-tasks/1` JSON任务，不是ONNX、模型权重或自然语言。输出为母控、局控0、局控1三份v2/64 bit镜像、128 bit PM字、SHA/CRC及主机装载计划。已有控制RTL和Block数据通路保持不变。

## 已绑定的目标

| target | 实际顶层 | 两端类型及拓扑ID |
| --- | --- | --- |
| five/U、F、C、P、J | five_boot_top，KIND=0/1/2/3/4 | 双U、双F、双C、双P、双J；0x01930011+KIND |
| recovery/U、F、C、J | recovery_boot_top，KIND=0/1/2/4 | 源0为U/F/C/J，目的1为P；0x01930500+KIND |

ABI固定0x01930001，容量ID0x17630001；三个PM各16 KiB，单clk_i，同步主机。目标周期仍3.333333333 ns。task.block_type使用此原生ABI的KIND枚举；不能套用早期通用ISA文档中的Block类型编号。描述符resource=0、required_resources=1代表整组适配器服务槽，不能据此认为每种操作都只使用M宏。

每端一份常驻任务、每作业各CALL一次、每端一个在途服务。两个CALL均先于共同G_WAIT，可选择0/1或1/0顺序、两个不同的0..7令牌。局部按L_EXEC/L_WAIT串行执行，末尾L_END。当前编译器不生成动态形状、循环、条件分支、多任务驻留或任意路由。

## 输入合同

顶层必须恰好包含schema、name、target、epoch、generation、job、sequence、image_ids、tokens、call_order、buffers、tasks、transfers。整数不能用boolean替代；未知字段、重复JSON键及非法版本拒绝。image_ids为三个不同非零uint32；epoch/generation/job/START sequence为非零uint32，J epoch只允许1..255，不自动绕回。运行时仍须保证启动序号与epoch水位满足实际硬件历史；示例每次从新复位组运行。

缓冲区字段：name、block(0/1)、base_bytes、words、space、format、initial。地址16 B对齐，容量和整个范围在私有16 KiB S内；同端点任何两个声明的物理范围不能重叠。format仅RAW128，意味着逐位传输，不提供数值格式转换。initial=true是“主机必须完整提供输入”的前提；编译器不凭它证明输入数值合法。read-before-produce、错误端点引用、输出别名及容量溢出拒绝。

普通类型space=S；J输入为J_FRAGMENT0/J_FRAGMENT1，输出为J_OUTPUT（base_bytes仍指定实际输出存储位置，读取/发送使用T提交输出，不允许伪装普通S读取）。J两输入与输出长度相同，最多4字，JOIN后必须RELEASE。

| semantic op | 字段与当前准入 |
| --- | --- |
| ucf | lane/meta/src/dst。U：N的0x100/0x81/2/0x85/7与E的3；F/C：G的9和E的0；C另有R的0/2。逐项核对源数、是否存储、上下文顺序。meta是该原生ABI的命令，不是64 bit执行opcode。 |
| p_load | a、b，均已初始化且至少4字，64 B对齐；固定首轮一行一tile配置。 |
| p_config0 / p_config1 | 无额外参数；固定已验证的M配置序列，先load，再两次配置。 |
| p_store | dst，固定已验证的M存储命令，不隐式开启pack16。 |
| p_gate | a、b、dst；两个已就绪输入，目的不与输入别名。 |
| join | left、right、dst、tag。绑定J片段0/1，24 bit tag与本次epoch组合。 |
| release | 无额外参数；显式结束J本次lease。 |

ucf的具体元数据仅开放已接入且有测试的有限子集，未开放裸native0..3逃逸口。N要求配置→读入→统计完成后才能归一化/读统计；R要求load后read。编译器的能力校验不能替代宏对数值参数和运行时输入的检查。

## 跨Block与服务序号

five/*要求transfers为空；recovery/*要求一条连续、1..4字、源0→P1的RAW128传输。字段source/destination/words/format引用声明缓冲区，两端长度必须相同。源结果必须已经产生，目的声明为未初始化。

编译器在源原生操作之后追加SEND；在目的原生操作之前插入每字的RESERVE、RECEIVE。RESERVE.native1由“源原生操作条数+字序号”生成，和源L_EXEC的service_sequence对应，不能把START sequence或目的服务序号写入该字段。J源SEND使用T输出index0..3，其他源使用实际S字地址。完整任务/作业身份仍由MC/LC运行时产生，并由第6步提交/ACK和恢复电路核对。

## 镜像、装载与独立核对

compiler.py复用既有pack_image/64 bit编码器，规范化JSON后确定输入SHA，生成镜像头、局部task、128 B execution表和指令；按本profile最多16条展开后的服务检查，程序/PM容量都检查。三个image_id、ABI、topology、capacity、task/header身份一致。

audit.py不导入compiler、codec或image，独立用规范等式构造完整字节串，核对所有头、填充/保留位、指令、task、执行记录、SEND/预约服务序号、SHA及CRC。它不是第二份硬件数值实现。reference.py另做小数值参考，覆盖已声明示例域；N限精确RMS样例，G覆盖零输入sigmoid门控及SiLU门控，M为固定一行/tile例，C检查状态载入/读回，J为八路饱和加法。不能将其解释为任意模型数值等价。

host.py把镜像变成RELEASE→BEGIN→逐128 bit写→逐字读回→VERIFY→PREPARE→DEPLOY计划。资格检查计划有意包含未部署START、错误ABI BEGIN等期望失败命令，记录expected status；它是可回放的验证/接入计划，不是可忽略回复状态的生产驱动。主机要在DEPLOY后按声明提供输入，再START、轮询并消费RESULT。J用命令14输入、13消费提交输出；普通S用12写、11读。

```bash
python3 -B project/control_task_compiler_v1/compiler.py task.json --output bundle.json
python3 -B project/control_task_compiler_v1/emit.py task.json bundle.json --out /path/to/audited-images
python3 -B project/control_task_compiler_v1/test_compiler.py --out /path/to/software-report.json
python3 -B project/control_task_compiler_v1/generate.py --target recovery/U /path/to/examples
KIND=0 LAYOUT=1 NATIVE_STAGE=/path/to/stage SRAM_BANK=/path/to/bank.v VERILATOR=/path/to/verilator BUILD_JOBS=4 bash project/control_task_compiler_v1/run.sh /path/to/results
```

输入完整样例及数据由fixtures.py/example产生，也提供example-task.json/example-inputs.json；schema.json为形状合同，编译器额外执行语义检查，targets.json列出绑定目标。emit先完成独立核对再写三个bin/mem和清单；compiler CLI遇非法输入不覆盖已有输出。测试原子写使用同目录临时文件。

## 验证边界和接续

软件测试包含27个正例（九目标×三配置），1134个重新计算自洽SHA/CRC后的编码变异检测，52个非法输入拒绝、3个CLI输出/导出保护及2个机器清单核对，共1218检查点。硬件回放矩阵为九目标×两PM后端×三配置×三初态/种子，共162场景；每配置改变数据/地址、epoch/generation/image ID、令牌或CALL顺序，实际结果以[技术索引](../../work/Melodydt/179/control-compiler-validation.json)为准。软件通过不等同RTL通过。

新增tb只通过主机接口装载/核验镜像、供数、启动、消费结果，检查完整S/T输出、确认写字节、提交/ACK及回复背压；旧控制RTL不修改。功能bench仍10 ns匹配bank模型，未修改实现目标周期。第6步624项恢复矩阵为历史已验收证据，本轮不冒充重新执行。定向通过率不是功能覆盖率；组合STA/面积功耗/CTS/物理未执行。

第8步补齐完整类型、状态及异常组合与覆盖，第9步冻结综合文件/参数/边界/SDC。完整LLM图导入、分片、算子选择、任意规模调度与数值格式转换仍在本有界编译器之外。
