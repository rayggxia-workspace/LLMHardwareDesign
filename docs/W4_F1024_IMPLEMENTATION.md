# L4 F1024：真实尺寸FFN整数执行与N-long

Issue151 / PR152，负责人Melodydt。输入`75d99a5ba01adba1e978db3933a41e1d43c49c30`，实际服务器源码`6a7de2c8c3368f7e82005ac7f194071c6b6474bf`。新增2RTL/2TB，原40份RTL/TB/include逐字节不变；不修改原生七宏，不改变原N/F16/A16/AF16。当前仍L4，L5没有开始。

本轮把仓库Qwen3-0.6B的**H1024/I3072、单token完整FFN结构**落实为可执行整数顶层，服务器95245/node1/c64/8CPU/Verilator5.042通过N-long38、F102426共64CASE，Slurm自然COMPLETED0:0/2分11秒。两个完整样例每个实际接收9MiB权重且SHA一致；另一个完整计算样例验证输出首字已消费后的abort。训练模型质量仍UNKNOWN：尺寸相同、整数参考一致不等于真实模型精度通过。

## 为什么需要这一步

原F16只验证H8/I8，旧N控制器上限257；不能通过把实际模型缩成8维来签收H1024/I3072。新增[N-long](../project/rtl/block_connection_w4/block_w4_n_long_ctrl.sv)扩展字数/index/偏移/末字判断至128个128bit字，保持全部1024项统计与同一个factor回放。新增[F1024顶层](../project/rtl/block_connection_w4/block_w4_f1024_top.sv)负责固定程序、S所有权、完整归约、参数握手及终态；没有新增独立bridge宏或改变叶宏接口。控制器和适配器属于预制有源逻辑候选，参数内容可以更换，运行时不能改变算法顺序。

## 固定程序与数值

1. 256个入口字写入真实S：128字X、128字gamma。每次写ACK退休，最后ACK后才允许start；捕获非零weights_version和新job。
2. 写12个宽A容器padding字为真zero；N-long RMS处理完整1024项，X/gamma128字，Norm128字。
3. 对384组、每组8个中间通道，gate先32个K32 chunk完整归约，再up32chunk；分别量化保存，再G fn0做SiLU(gate)×up，直接写紧凑mid数组。
4. 等全部3072个mid建立后，down128组，每组96个K32 chunk完整归约。每组与保留的原X做E加法，形成完整1024输出。
5. 输出全部建立后T BEGIN128，逐字填充、COMMIT、DRAIN，最后实际RELEASE后才正常DONE。输出stall保持data/index/last；已消费prefix不能因abort回滚。

每个完整M输出组只CLEAR、SCALE一次；chunk0 EXEC descriptor0xc885，后续0xc881保留raw累加。最后chunk才READ5/index0,1/0x107，统一RNE7/clipS16。禁止每chunk先截成S16再求和，也禁止同一个M归约上下文中插入其他projection。

selected合同：X/gamma/Norm/mid/output为S16 Fin10，权重S8 Fin7，M raw Fin17；G门乘RNE10，E残差shift0，逐stage饱和OR。epsilon code1实际为2^-20，**不等于源1e-6**。详细公式与独立参考见[数值合同](W4_F1024_NUMERIC_CONTRACT.md)、[来源/质量门](F1024_SOURCE_QUALITY_REVIEW.md)。

## S/T生存期与layout

| S字地址 | 数据 | 预约字节 |
| --- | --- | ---: |
| 0..127 | 原X，残差完成前不可覆盖 | 2048 |
| 128..255 | gamma | 2048 |
| 256..383 | 完整Norm，供全部gate/up | 2048 |
| 384..767 | 完整mid3072，供全部down | 6144 |
| 768..895 | 完整输出 | 2048 |
| 896..911 | 四个512bit宽A容器 | 256 |
| 912..927 | K32×N8的四B8 tile | 256 |
| 928..931 | gate8/up8/保留scratch/down8 | 64 |

固定预约932字14912B，S宏仍16KiB；T用128字2048B，宏仍6KiB。每chunk从compact Norm/mid读4个实际字，分别写A容器896/900/904/908，其他12字真zero。不能把紧凑数组直接当loader的宽容器。LOCAL/N/G/E唯一普通S owner贯穿整个服务到目的写ACK和response消费；loader在独占阶段使用宽口，再向M送4A/4B tile。

## 9MiB供参与协调

每次请求携带job16/seq16/version16/matrix2/group9/chunk7；一次在途，固定算法顺序，provider仅供应参数。返回128bit数据及job/seq/version/index/last/error，严格16字/index0..15/last仅15。当前字capture后，必须等S912+index真实写ACK，才接受下一当前字。

gate/up矩阵各3072×1024、down1024×3072，合计9437184个S8字节。每条完整行有36864次EXEC/请求、589824个128bit权重拍。实测正常服务总数由TB独立monitor检查：普通S888076次=739084写+148992读，M命令40448，N native258，G384服务/1536pair，E128服务，loader36864次/294912次宽读，T128字/一次RELEASE。

job初次1，abort/叶复位不重置job counter，65535之后拒绝start防静默回绕；seq逐成功EXEC推进。version只在start捕获。旧job/旧seq可排空，不写S、不改当前数据计数；当前/未来错误tag、version、index、last、matching error在RX接受时产生errorDONE。hard reset必须协调provider清在途，不能保证任意独立warm reset和无限晚返回。

此接口解决参数流入的有序性与版本隔离，**尚无真实外存控制器**，不规定最后采用片外DRAM或其他存储服务；保留用户要求的外存灵活性。也不是L5通用岛间stored ACK：本顶层host out_ready仅是输出take。

## 实际验证与证据

| 检查 | 实际结果 |
| --- | --- |
| 服务器N-long | 38唯一CASE，三mode1..1024、1023/513/257/tail、地址端点、ACK/poison/reset |
| 服务器F1024 | 26唯一CASE，两个完整数值fixture、一个完整计算输出prefixabort及早期故障 |
| 权重实流 | 两个正常fixture分别9437184B，actual accepted流与独立canonical长度/SHA一致 |
| 独立数学/静态 | 112717断言；48个未按周期合并的完整K直接dot验证参考加速等价；不是RTL测试 |
| 管理检查 | check_project PASS，仅管理结构 |
| 旧源码 | 40份逐字节不变；本轮旧RTL回归未执行 |
| 编译警告 | N-long 67、F1024 33条保留；不是lint clean |

错误/回压覆盖输入最后ACK启动门、权重写ACK门、请求保持/version绑定、错误index/last/job/seq/version/error、stale排空、取消后旧tag隔离、prestartabort/reset、N/M/G错误、S helper错误、zero version、job耗尽和heldM reset。旧job取消测试合成重放旧tag，不泛化为所有phase的provider排空活性；新top未单独注入nativeE错误。S宏无独立error pin，helper错误注入验证控制器策略，不能当实际MEM故障验收。

[运行原始回执](../work/Melodydt/151/f1024-rtl-evidence/runs/r02/results/run-receipt.json)、[全部文本SHA清单](../work/Melodydt/151/f1024-rtl-evidence/evidence-manifest.json)、[源码Git/SHA证明](../work/Melodydt/151/f1024-source-inputs.json)、[大数据/脚本索引](../work/Melodydt/151/f1024-evidence-index.json)。30份输入与18份文本及归档SHA已核验；四份9MiB canonical/accepted文件在导出时再次核验，原始数据和构建只留`/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/f1024-75d99a5-20261102`。

实际源码为6a7de2c8；先前43e9f48已推但未运行，r01只在本地打包未提交服务器。提交前修了N-long总结行及runner对CASE枚举顺序的假设，所有有效CASE/重复/数量/summary/失败检测保留。实际只有r02/95245，没有编造首轮失败作业。

## 数值质量与下一步

历史来源确实记录Qwen3加载过11个训练层tensor；本轮没有访问其他成员目录，也没有可读获授权的量化三矩阵/gamma/代表性F输入交付。当前两个fixture是合成数据。独立FP32 counterpart诊断：dense最大绝对误差122676.7734375、RMSE43916.28786715324，且整数饱和；gamma0误差0。这是该压力样例的诊断，不是trained-Qwen3测试，也没有设阈值宣布质量通过。

下一工作先获得获授权的layer0 tensor和F切口输入/FP32输出、校准/独立评估集及误差门，冻结每stage scale/epsilon/clip并评估是否需要新增重定标硬件。硬件尺寸通路可复用，不能绕过数值门。原八模型×三target24项GAP、质量UNKNOWN账本保持不变；新profile只签收所选整数函数。

L4结构扩展的下一独立项是实际Qwen3 Attention：H1024、Q16/KV8、D128、Q宽2048≠H、GQA2、Q/K head RMS，以及位置/KV/Softmax/容量供参；不能把当前A16单头H8直接扩大名字当实现。真实A/F签收后再进入L5母控/双岛stored ACK/一般拓扑。完整28层推理、其余样本、永久M11/M12绑定、真实MEM和PPA仍待实施。

## 交付状态

复用task/151-six-connection-study→task/143-seven-block-v2及PR152，Refs #151；待外部审查，不合并、不done。登记management-hub PR5 open/unmerged、默认登记表无本project_id，pending。配置只有labels/status-mapping，没有board.json且无Projects条目工具：实际看板unverified、同步pending，处理人待指定。不是证实账号被拒权限。最终文件commit和在线读回见PR回执。
