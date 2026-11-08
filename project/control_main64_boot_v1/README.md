# R8.1 / R8.2：main64能力合同与统一部署顶层

Issue179 / PR180，Melodydt。源main c4d7b960，分支起点f087c3c8。保留main原始RTL和生成器，生成模块按类型作可逆标识符重命名，防止U的三源adapter与C/F两源adapter撞名；P/U未使用的close输入固定0，诊断输出显式空接，J专用适配器10个未用输出作可逆的显式空接。禁止旧frontend native_lc()覆盖main P/U局控。

## R8.1 接口与能力合同

`contract.json`由`contract.py`生成，区分硬件原生能力和本阶段资格范围。统一两目标、8个母控token、每端一驻留任务/一服务在途，64位执行指令，128位PM口，单时钟3.333333333ns。母控/局控镜像当前容量分别4736/8320字节，物理PM每端16KiB、四bank；容量不等于都可编成16KiB程序。每端最多256条指令、16个execution描述符。ABI0x01930001，capacity0x17630001；局控ID0/1；cohort topology=0x01938000+KIND0*16+KIND1，母控与两个局控必须相同，Block类型单独记录。主机BEGIN拓扑不匹配立即拒绝。身份、cfg、任务/返回端口逐位与五类main实际生成接口核对。

| 类型 | main原生能力 | 当前主机数据口与直接通路 |
| --- | --- | --- |
| U | 0x100命令、0x101发送、0x102接收、0x103预约、0x104配对直接运算；E最多三源，N最多两源 | 可写入初始化，无普通S_READ端口；读回结果经真实SEND。N→E128位闭环，保留独立TX保持槽。 |
| F | 0x100..0x103；E/G最多两源 | 主机预部署写、空闲读；G→E32位闭环。 |
| C | 0x100..0x103；E/G最多两源，R最多一源 | 主机预部署写、空闲读；G→E32位闭环，R上下文顺序仍由程序保证。 |
| P | 0x110装载、0x111矩阵命令、0x112门控 | 主机预部署写、空闲读；M→G32位闭环。仅在其LC READY时允许对端被动写入。 |
| J | 0x120汇合、0x121释放 | 专属片段写和已提交输出读取；E→S128位闭环。候选限定一任务一次join、最多4输出字、epoch1..255。 |

主机目标0/1/2分别为母控/LC0/LC1；3为整组。管理命令0..12复用既有boot manager，并非执行指令。13/14为J输出读取/片段写。普通S初始化要求在DEPLOY前完成，部署后S_WRITE返回BUSY；J片段可在空闲且旧输出已消费后补充，每次join消耗片段租约。U/J普通S_READ及J普通S_WRITE返回unsupported，不能挂起等待不存在的端口。C/F读取使用main group_top已有verify_read选项形成候选主机读口；这项新封装不继承原物理资格。

R8.2手写程序仅以G_CALL/G_WAIT/G_END和L_EXEC/L_WAIT/L_END取得集成资格；主ISA编码未改。main P/U的取指移植不代表自动支持PR180全部新指令。`native_sources()`是工具端能力核对，不替代main RTL准入，也尚未接入R8.3编译器。

## R8.2 硬件组成与执行

`main64_boot_top`接统一主机valid/ready命令；`main64_control_top`实例化main mother_control_64（含一个PM），两个main64_endpoint和两个额外PM。每个端点绑定main自身生成的局控/服务/实际数据组。共1MC、2LC、3PM、12程序bank；Block私有S/T另计，DUT不实例化network_pm或测试台供数通道。

装载顺序：整组RELEASE→各端BEGIN→顺序WRITE16→完整READ16→CRC/格式VERIFY→PREPARE→预置S或J片段→共同DEPLOY→START→RESULT。CRC按实际存储器响应计算，版本/角色/ABI/拓扑/容量和generation均检查；host无proof旁路。复位清协议不清存储数组，必须重新装载。

KIND0/KIND1选择九种有界配对：U/U、F/F、C/C、P/P、J/J、U/P、F/P、C/P、J/P。U/U验证两/三源FMA、同时SEND以及目的S写入后再读出回送；U/F/C到P以实际SRAM响应ACK验证被动RAW128复制，不声称数值格式自动兼容。J/P本阶段只验证两个类型同组部署和独立计算，J→P提交链留R8.4。完整身份/取消/隔离监督、编译器集成、全覆盖和新组合STA分别是R8.3–R8.6及后端工作。

## 复现与范围

```bash
python3 -B project/control_main64_boot_v1/test_contract.py --out /results/contract.json
# 下面仅在获授权服务器Slurm分配内执行
python3.12 -B project/control_main64_boot_v1/stage.py /results/stage
python3.12 -B project/control_main64_boot_v1/run.py --stage /results/stage --pair 0 --out /results/u
python3.12 -B project/control_main64_boot_v1/structure.py --stage /results/stage --pair 0 --out /results/u-structure
```

生成器需要main锁定的#193 acceptance-02、#155 SRAM仿真模型和CFJ历史锁源。`stage.py`逐项核验main源锁、五类公共端口、模块重命名可逆性，并记录输出SHA。run.py只从主机口装载DUT内PM，不层次写存储数组；测试台只观察实际事务和结果。非法native_op=0xffff按main默认BAD_DESCRIPTOR=5验收，保留错误检查；重复J任务需重新提交其片段。回归包括正常、重复任务、装载中复位、读回CRC破坏、世代拒绝、ABORT恢复和非法native操作。

检查结果以本轮验证索引为准。接口合同软件检查不是RTL功能；通用结构综合不是映射时序/物理；旧1690例、main独立物理门和上轮123例不自动授予新统一top资格。

补充部署保护由guards.py运行，使用主矩阵同一套DUT源码，检查部署后坏ABI/坏拓扑BEGIN不撤销旧部署、旧镜像仍正常执行及部署后普通写被拒绝。它与主矩阵存在业务路径重叠，执行次数不等于独立覆盖项。collect.py --root PRIMARY --guards-root SUPPLEMENT --out PRIMARY/collected.json逐项核对日志/镜像/源和两组DUT一致性。
