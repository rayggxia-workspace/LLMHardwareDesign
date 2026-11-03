# L5/H2 G1实现边界与剩余验证

> 主线五G1首切片最终：源码7a656a3fe4a86342d24b72ebecdc524052bf86d7，96208/n03/node1/c64/8CPU自然COMPLETED0:0/3分1秒；12终态定向+18实际AF及10actualSHA通过。另unit96170的DMA29/SEQ30通过，共89项不同预声明检查，非全图证明。n01/96183原18项成功、n02/96192失败及12项组件成功均保留，不把失败整合当通过。当前无本任务在跑作业、无自动监测。

2026-11-03，Issue151 / PR152，Melodydt。本文只读审查当前新顶层、顺序器、executor和edge DMA，未修改运行源码或TB，未启动本地RTL/数值、服务器或物理流程。实际终态与交付状态由根任务回执记录；本文不是外部PR批准。

本次审阅收到的状态为：单元作业96170、源码a3ef…已有DMA29/SEQ30通过；完整AF作业96183、源码30a00e22…已通过编译、仍在RUNNING。**本文不预写完整AF通过，不把单元59项替代系统18项结果。** 系统结束后仍需严格CASE集合、退出码、实际输入/参数/权重/输出SHA及源码绑定。冻结前的准备合同状态不替代实际运行回执。

## 1. 现在实现的域

当前完整系统目标只验证H1的G1：物化初值X→A2→顺序两次F1→外部目的端。固定H1024、Sq2、Q16/KV8/D128、F intermediate3072，S16 Fin10、S8权重Fin7、epsilon_code1。F2是两个F1调用，不是原生双行F入口；参数包含A的192字及每行F的128字gamma，hidden和参数整帧stored后才启动原生kernel。

资源候选为M2/N2/E2/G1/R0/S3/T2共12叶：既有A/F各自的S/T，加新增16KiB edge S；四个4KiB槽、一普通口owner、一个数据字在途。SEQ状态、DMA的128bit holding及1024bit有效字元数据、executor计数/holding均是额外有源成本。外部目的S/helper只属于系统TB的真实接收端，不能无说明计入或删出产品BOM。

G1正常控制为48次ROM读取、7个内部动作、41条独立服务。内部动作为ALLOC×3、FREE×2、SETOUT和HALT；其余服务均须接受请求后再接受独立完成。G1的8次edge DMA应有1536次普通S请求/ACK，即768W+768R。每个完整job仍真实供应A6MiB和两行F共18MiB权重，不因版本相同假设缓存命中。这里是验收预期，不能代替系统结束后的逐job实测。

## 2. 两处顶层修复的作用

### 先完成初值导入，再接受父start，最后发首个ARM

[顶层](../project/rtl/block_connection_w5/block_w5_af_top.sv)的`dispatch_permit`对ARM要求已锁存`parent_started`；它同时门控顺序器所见的`svc_ready`和executor所见的`svc_valid`，不能一侧认为接收而另一侧未接收。IMPORT和WAIT_STORED可在此之前推进，先建立真实edge写ACK和`input_stored`，不会因等待start挡住形成start_ready所需的输入。

父start被接受时，顶层和executor分别锁存该事实；下一拍才开放ARM。新job接受或reset清顶层latch。`ARM`建立wrapper义务，原生START仍在hidden及参数完整存储之后；不能把ARM、hidden部分确认和整帧stored混为同一事件。

### 已有DONE后不把外部abort重新写进executor

顶层向executor传递`(abort && !done_valid) || cohort_abort`。顺序器已有DONE时保留终态并允许ready同拍消费一次；若此时仍把外部abort传给executor，会重新置poison、复位子树/F编号，并可能改变`done_partial`等已呈现状态。现在已有DONE时屏蔽这条外部abort路径，内部错误产生的`cohort_abort`仍有效。

该修复不意味着任意复位不影响完成。hard reset仍取消义务而不补DONE；DONE消费后若外部继续保持abort，后续空闲cohort仍可能被复位。它也不提供独立warm-reset、断电恢复或无reset晚返回隔离。

## 3. 字段验证和信任边界

| 接口 | 当前检查/保持 | 尚不能据此保证的内容 |
|---|---|---|
| 永久ROM请求/返回 | 单请求，记录holding；拒绝未知opcode、flags/保留字段、非法顺序/长度/对象及PC。当前只接受线性next，IF拒绝 | 不是任意H1图运行时；无host程序下载。ROM端口模型不证明M11/M12位单元、读周期、ECC或抗篡改 |
| 对象描述符 | 17项、固定shape/Fin/layout/profile、版本/字节数、consumer count、producer id、保留字段；四槽first-free，单赋值及引用检查 | 512bit组合读口是候选表边界；semantic摘要不是运行时张量内容校验，真实镜像完整性还依赖离线编译和源码/输入SHA |
| 内部svc | 顶层只接固定SEQ输出；每条accept后等done。action response不自动消费后续WAIT屏障 | executor不是独立通用host命令入口。并非在executor重复校验SEQ已经验证的全部flags/字段；绕过SEQ直接驱动不在接收域 |
| 参数provider | 请求id/island/row/words在等待中保持；响应逐字检查index/last/error，最终等待原生整帧stored | 响应没有返回parameter id、generation或version。不能识别复位后同index的旧参数；符号引用不等于真实权重manifest或MEM服务 |
| A/F权重 | 两口保留子kernel位宽/版本和原策略；活动任务对请求/返回对称门控 | A严格拒绝与F旧tag drain策略没有被统一。版本不是Fin选择；当前executor仍baseline，不因95979独立W8 F回归自动变成W8 AF |
| 最终输出/ACK | 输出保持到匹配index/generation的显式目的确认；错误ACK形成错误而不成功退休 | ACK端不检查外部存储器的物理写入，只检查协议。系统TB用真实S/helper生成ACK；真实产品仍须保证接收端同等合同 |

当前metadata与ROM不是运行时可更换程序。其读出电路、路由/holding、译码和端点均须在M1–M10冻结前存在；M11/M12只能编码/连接既有资源，不能补MUX、仲裁、寄存切片、CTS或驱动。程序记录128bit及H1镜像字节数不是ROM物理面积或金属编码资格。

G2同岛重入、G3 fork/SELECT尚无本轮系统执行证据；不能因SEQ字段或PC有余量就声明支持。CALL/RETURN、运行时LOOP、被跳计算分支、反馈、更多并发、D/H/R/NUM、MoE及通用MEM仍须各自版本化合同和测试。特别G2/G3需要四次F start的整图预算，当前G1的两次预算不能直接推广。

## 4. ACK、租约和错误保持

[edge DMA](../project/rtl/block_connection_w5/block_w5_edge_dma.sv)写端会先捕获保持中的offer，实际普通S写ACK消费后才给`in_ready`退休许可。源必须持续保持valid/data/index/last，不能把捕获当作源已退休。用于A/F输出时，原生T只在目的edge真实S写ACK后take；完整存储、CLOSE、实际RELEASE和DONE仍分开。

[executor](../project/rtl/block_connection_w5/block_w5_af_executor.sv)的LOAD用`hidden_pending`区分child接受与edge源退休：先让child捕获一次，等待这个固定kernel输入口经真实S ACK重新开放ready，再退休edge字。该推论依赖已锁定A/F非末hidden输入的具体合同；不能把所有ready信号无条件解释成stored ACK。PARAM的末字捕获也不等于完整帧stored，WAIT_PARAM仍等待原生`input_stored`。

DMA action可在done_valid已建立时返回服务response，但保持该DMA完成供后续WAIT消费；只有相应WAIT服务成功才更新顺序器的存储事实和引用。F row1的128字偏移由executor加，SEQ传整槽`slot<<8`；没有两侧重复加偏移。

已经offered的服务RESP在错误/abort期间保持内容，不因poison撤回。SEQ错误DONE时不再接收该response，下一job_begin清旧mailbox。原生子树静止与一个保持的服务完成记录可以并存；不能用“所有valid必须为0”误判已关闭cohort。对于非合法协议输入，fatal检测可立即门控数据/请求并进入协调错误路径，不宣称故障前已呈现的payload仍能永久保留或回放。

运行中的executor计数只计匹配的最终目的ACK；公共`done_words`只在done_valid时读取，完成事件中锁存该计数；`done_partial`锁存error且计数非零。若接收端已经捕获或真实写入、尚未来得及返回ACK，错误时计数仍可能为0；因此`partial=0`不能证明外部没有可见副作用。已确认输出前缀和真实RAM写均不回滚，没有跨S/T/目的存储的全局原子性。

ROM返回、参数、权重provider必须参与同一cohort的停止/清理；系统TB在`child_reset`时清这些在途模型。F原生job16及mirror在cohort reset后会重用，参数/ROM返回本身又没有完整任务tag，当前不具备任意外部无限迟到响应隔离。正常任务之间无reset复用是另一条独立验收，不替代该限制。

历史静态发现及最终修复：原30a/n01在EXPORT已有确认后若后续ROM报错，SEQ先呈现errorDONE，下一拍poison才使live partial变化。最终263c/n02引入completion_hold、7a656/n03沿用相同RTL，在单次capture冻结完整tuple且计算error&&words!=0，public终态保持时禁止新job；不再转发live executor flags。12项组件定向测试覆盖延迟字段变化/前缀1与256/保持/重复/复位，最终18项G1及10流回归通过。n02的系统TB观测窗口失败和n03修正保留；系统级EXPORT后ROM错误、RUN故障及prefix取消仍未做完整注入，不能以组件测试声称全部系统故障覆盖。

普通S原生没有error/ECC口，helper的成功确认不表示有任意物理存储故障检测；已有TB合成错误也不能授予该能力。公平返回和有限外部背压仍是进展前提；无服务完成时顺序器会等待，不提供已验证的最大恢复时延或通用抢占。

## 5. 当前用例覆盖与后续门

[系统合同](../work/Melodydt/151/h2/af-contract.json)预声明18项：空闲abort、ROM未知码/错误、输入元数据、部分输入abort、ROM/IMPORT reset、F版本0在A前拒绝、参数index/last/error及请求取消/reset，以及两次完整G1和真实目的S ACK背压。完整job使用继承独立数学golden，参数/权重按真实接口发送，不用DUT结果制造期望；第二次完整job前无reset，并检查F mirror从2到4。

这18项没有覆盖新wrapper中途M/N/E/G native故障、完整计算期间的取消、最终输出prefix取消、错误/重复/晚目的ACK、跨复位无限晚返回、G2/G3、所有metadata/对象容量组合或多时钟域。原内核旧测试仍绑定各自历史源码/用例，不能转写成本轮母控已测。单元SEQ30使用mock服务，仅验证母控协议，不是A/F数值；DMA29也不代替完整系统路径。

最终96208已核验12+18标记/两正常job及10actualSHA；下一继续主线五，补产品级参数/编号预约、G2/G3和上述故障门。L4训练参数完整整数AF质量、24项旧模型GAP、真实MEM和共同底座物理均保持独立。即使该固定G1最终功能通过，也只能说明所测共享表顺序器/端点路径成立，不等于整个L5、H2/H3或产品永久绑定已完成。
