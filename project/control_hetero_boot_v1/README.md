# 异构控制与实际提交ACK：综合前第5步

Issue179 / PR180，Melodydt。复用当前v2/64 bit MC/LC、control_pm、公共装载管理器及原生组数据通路，新增hetero_boot_top和定向原生服务适配。目标周期保持3.333333333 ns。

## 声明的拓扑和数据合同

编译期KIND=0/1/2/4分别选择U/F/C/J作为目标0；目标1固定P。本版支持U→P、F→P、C→P、J→P四条定向RAW128链。每个任务恰有一次CALL0和一次CALL1，两个端点的任务序号配对前进；不支持不对称CALL历史、任意路由、多跳、反向链或五类同时驻留。异常任务后的完整取消/恢复属于第6步，当前恢复使用共同复位及三端重新装载。

每次转移为一个128 bit字。U/F/C源为实际私有S的保持响应；J源为实际T提交输出捕获FIFO，源地址解释为T输出index（0..3），并核对该包实际job/epoch/task_sequence。J的一次JOIN至多4字，结果逐字发送；未匹配ACK前不pop。目的均为P实际私有S，按16 B字节地址读回完整128 bit。

无隐式舍入、缩位宽或数值格式转换。示例U发送两源FMA结果，F发送G/E结果，C发送R状态，J发送四字合并结果。目的P在RECEIVE完成后执行读取已提交S的G服务（示例乘数为0，检查控制顺序）；数值传输本身用目的128 bit实际S读回与独立参考核对。

## 身份、预约和完成

物理端点固定源0→目的1，路由归属由冻结拓扑隐含。每字另带128 bit身份：job[127:96]、epoch[95:64]、源任务序号[63:32]、源服务序号[31:0]，均来自实际LC服务请求。目的预约地址和完整期望身份必须同时匹配才产生真实写请求。

目的期望job/epoch/任务序号来自自身配对CALL的实际身份，期望源服务序号由预约描述符指定。身份字段不能拿主机job_sequence或PC替代。每任务的源服务序号从0递增，源程序中SEND的执行描述符序号就是本例应预约值。

链路握手顺序：源保持S响应或J输出 → 链路锁存字/地址/身份 → 核对预约 → 请求目的P写入 → 等实际P存储响应握手 → store_commit → 返回原身份ACK → 源独立确认commit已见且128 bit身份匹配 → 释放源并回报服务完成。早到、旧世代、其他job/任务/服务的ACK不能释放源。字链路及源端分别保存完成资格，ACK不会仅凭valid生效。

链路所有权、未消费J输出、预约或在途存储响应均纳入link_pending_o，公共入口禁止新START/镜像或S修改。完整工作结束必须排空这些义务。commit_count_o计真实目的写提交，ack_count_o计源接收匹配且有提交资格的ACK；它们是本复位组内累计字数。

## 程序编码

以下为原生L_EXEC描述符的native_op，不是新增64 bit执行指令，也不是主机管理命令。

| native_op | 端点 | native0 | native1 | native2/3 |
| --- | --- | --- | --- | --- |
| 0x101 SEND | 源0 | [9:0]源S字址或J输出index；[19:10]目的P字址；高位0 | 0 | 0 |
| 0x103 RESERVE | 目的1 | [9:0]目的P字址；高位0 | 期望源服务序号 | 0 |
| 0x102 RECEIVE | 目的1 | 0 | 0 | 0 |

描述符native0..3分别位于[543:512]/[575:544]/[607:576]/[639:608]；[1023:640]保留0。其余执行描述符头、resource/service及native_abi_id沿用当前合同。服务反回16 B源读或16 B目的确认写；原生计算统计分别保留。ABI=0x01930001，成对topology=0x01930500+KIND；源block_type=KIND，目的block_type=3。

装载命令沿用0..12。J源额外保留管理命令13/14，目的P仍允许普通S_READ/S_WRITE；J的原生epoch仍限1..255。实际程序通过BEGIN→WRITE16→READ16→VERIFY→PREPARE→DEPLOY装载三端PM，再START。DUT没有测试台存储或伪造的目的写完成。

## 复现与验收边界

使用[冻结依赖输入](../control_frontend_v1/upstream-lock.json)构建stage。功能测试加载真实原生组与合格bank功能模型；结构综合把数据组和bank标为明确边界，仅验收控制/连接，不声称新增组合时序或物理通过。

```bash
KIND=0 NATIVE_STAGE=/path/to/stage SRAM_BANK=/path/to/bank.v VERILATOR=/path/to/verilator BUILD_JOBS=4 bash project/control_hetero_boot_v1/run.sh /path/to/results/U-P
python3 -B project/control_hetero_boot_v1/check.py --kind 0 --stage /path/to/stage --bank /path/to/bank.v --verilator /path/to/verilator --yosys /path/to/yosys --out /path/to/structure/U-P
```

依次选择KIND=0/1/2/4。每链两种PM后端、七模式、三种初态/种子，模式为正常、目的offer停顿、连续任务、链路中共同复位/重装、四字段错误ACK、错误预约身份、真实提交前注入正确身份ACK。测试通过率不是功能覆盖率；全部取消/故障矩阵和适用CDC在后续第6步补齐。实际结果见[技术索引](../../work/Melodydt/179/control-hetero-validation.json)。
