# 第1项：P消费者仲裁与DMA预取的实施合同

负责人 Melodydt；Issue247 / PR243；本轮输入快照为 `3a66f8de0889925846e9d737690e2d9e297bb173`。本文与候选代码只在隔离实验目录编写，生产文件没有由本子任务修改。SRAM容量保持16KiB。当前已实现的是**普通事务消费者优先仲裁候选**；真正的外部DMA描述符预取策略仍有下述接线与验收步骤，不能把整个第1项说成已完成。

## 1. 现有路径和准确的改动层

生产 `project/rtl/pu_leaf_base/pu_p_group.sv` 将 `{local_req,mem_req}` 送入 `pu_p_store_control`。client0/1是两个通用外部IO边界，client2是G读写，client3是M写回。因此 `CONSUMER_MASK=4'b1100` 表示本地计算消费者，不表示某个地址范围，也不等价于“读是需求、写是预取”。外部请求可能是完成下一LOAD所必需的输入写，不能无限饿死。

旧 `block_local_s_arbiter` 一次仅保留一个请求，从IDLE接收、SEND等待存储接受、RETURN等响应被原client消费后才重新准入。请求接受不等于写完成。旧 `pu_p_store_control` 在LOAD请求出现时先关闭普通请求准入，等待已有响应退休；之后由feeder完整任务独占，直到done被消费。`local_s_p` 同样显式维护普通在途计数与feeder分相。

本候选只替换普通仲裁选择，保持单请求在途、原三段状态和ACK归属。第2项若增加安全的普通/feeder并发，必须继续在LOAD边界drain，并由其真实存储包装器检查活动LOAD范围及存储冲突。本仲裁器既不持有LOAD地址，也不代替那些检查；不能将它自身的fairness计数解释为后端已经支持并发。

## 2. 新模块及兼容性

模块 `project/rtl/block_local_s/popt_s_policy_arbiter.sv` 与旧 `block_local_s_arbiter` 端口一致，增加：

| 参数 | 默认 | 合同 |
|---|---:|---|
| POLICY_ENABLE | 0 | generate直接实例化原arbiter，保留默认逐周期行为 |
| CONSUMER_MASK | 4'b1100（按CLIENTS截取） | 编译期显式client分类，不能按写方向动态推测 |
| MAX_CONSUMER_BURST | 2 | 有外部请求等待时，最多连续授权的消费者事务数；必须至少1 |

启用后两类有**独立轮转游标**。若两类都等待且消费者连续插队次数未到上限，选择消费者；到上限必须服务一个外部请求并清零计数。同类内部按自己的游标轮转。只使用一个全局游标会在每次外部授权后偏向同一消费者，不能满足内部公平。

任何选择只在IDLE发生。SEND遇mem_ready低时，owner、地址、读写及128bit数据保持；RETURN遇rsp_ready低时，响应仍归原owner，不能提前把请求寄存器交给下一client。新增消费者无法抢占已接受的外部事务。复位清除仲裁在途状态；真正存储内容是否保持由后端合同决定，本测试后端保留RAM。

## 3. 公平界与可测指标

持续等待的外部client，在L个外部client、消费者burst上限B下，最多被 `L*(B+1)-1` 个其他授权跳过。当前L=2，B=1/2/4对应上限3/5/9。该界针对能够退休的事务数，不是无条件周期界：mem_ready或原owner的rsp_ready无限背压时，不能既保留响应归属又承诺有限完成周期。两类内部各自轮转，消费者不会因为强制服务外部而互相饿死。

bench分别记录消费者从请求出现到接受的等待、到响应ACK的延迟、外部最大准入等待、外部最大跳过授权数，以及全部请求/存储提交/响应ACK。全体请求的总完成周期也保留。仲裁改变服务顺序可能降低消费者延迟，却不增加单端口持续吞吐；不应预先承诺整P或token/s提升。

## 4. 独立RTL验证

`policy_top.sv` 同时实例化候选和未修改原arbiter。默认模式每周期比较所有控制、请求数据和响应数据。启用模式连接一个有限、单响应、128bit字寻址的C++存储应答模型；其可变接受延迟、响应延迟和消费背压均由bench施加。此测试验证真实仲裁RTL，不把Python或SystemC改计时作为硬件结果，也不验证真实SRAM宏的端口能力。

`policy_test.cpp` 包括：

1. 四个client持续竞争，各自独立写/读回地址和不同数据；核对两类授权顺序及公平界。
2. 真实读写/ACK记账、随机mem_ready/响应延迟/rsp_ready，待响应期间禁止新请求。
3. 请求已接收后将源payload改为毒值；SEND长期背压时实际mem payload必须仍为已接收值。
4. 响应长期hold，所有新请求必须受阻；解压后逐一正确返回。
5. IDLE、SEND未存储提交、RETURN已返回但未ACK分别复位；禁止旧响应复活，之后新请求继续通过。
6. 默认逐周期对照；读响应翻位负例；实际生成“消费者游标卡死”的坏RTL负例，两者必须按指定错误失败，不能接受任意编译错误作负例通过。

运行器计划4种配置（默认、B1、B2、B4）×3个seed，共12次正向执行，另2项负例。每个配置的确定性饱和阶段用128笔事务，随机阶段用320笔事务，并另做hold/reset恢复；运行后以真实回执计数为准，不将计划数写成已执行数。

服务器入口（由主任务统一Slurm提交，禁止本地EDA）：

```text
python3 project/experiments/p_native_opt/run_policy_rtl.py --repo SOURCE --out RESULTS/policy --workers 4
```

依赖是原 `project/rtl/block_local_s/block_local_s_arbiter.sv`、新policy RTL、policy_top.sv和policy_test.cpp；Verilator5.042路径沿当前已授权项目环境。新的候选/bench严格编译，不增加`-Wno-fatal`。运行器要求有效的SLURM_CPUS_PER_TASK并保留命令、工具版本、输入及日志SHA。RTL编译/仿真尚未在本机执行；最终通过与性能数字以服务器result.json为准。

## 5. 与实际P的接线和回归

由主任务在独立集成目录给 `pu_p_store_control` 添加向下传递的默认关闭参数，并将其ordinary实例切换为新模块；所有旧端口与load/ACK语义保留。`pu_p_group` 同步向下传参，显式保持client0/1外部、2/3本地的映射。新的编译清单同时包含原arbiter（默认分支依赖）与新policy。

实际P回归至少包括原 `tb_pu_p_store` 的“未退休写阻止LOAD/feeder观察已写数据/done持有”检查，以及原 `tb_pu_p_group` 的两K段、写回、非法命令、SiLU、直连等价及复位检查。默认配置应同功能、同周期；启用配置保留全部数值断言，记录周期变化，不要求一定加速。第2项并发backend的地址保护/同址冲突等应由它自己的scoreboard另验。

在只有外部client竞争、只有本地client竞争、无竞争及短程序中，政策收益可以为零或负。若最终集成程序未提供持续竞争，不能仅以孤立bench的消费者延迟改善申领整个P的速度收益。

## 6. 真正DMA预取策略的接入步骤与依赖

本地生产RTL扫描没有发现可直接调整PR241模型`cfg.queued`的DMA队列。`project/experiments/pu_leaf_base/controlled.py` 是一个已有可追溯接入点：它从服务器冻结的Issue193控制包生成本地controller/native-service绑定，P端将descriptor译成load_fields和cmd_fields再接`pu_p_group`。当前load_fields只表达bank、rows、tiles、A/B位宽、reuse_B及A/B基址；它不是具备resident-A预算或prefetch-credit字段的生产DMA描述符。该外部控制包必须按原SHA读取，不能假装已经存在仓库内通用编译器。

后续工作按以下顺序形成可验收合同：

1. **编译期形状判定。** 固定实际S数据容量16KiB，依据A实际表示/行数、双A/B缓冲、部分和位置、工作区和写合并真实占用，产出每算子策略位与容量证明。单行静态权重且完整A能驻留时使用受限预取；长A、动态B、多行任务保持原策略。不能照搬S32模型的字节阈值到生产S16表示，也不能加入按workload名字选择赢家的表。
2. **版本化描述符。** 在native-service/局控描述符合同分配明确的新版本或能力位，增加策略、预取信用、buffer/region身份、epoch及边界长度；保留旧格式默认策略。不擅自占用原保留位；非法版本、超信用、地址溢出均拒绝。
3. **有限外部描述符队列。** 显式区分需求输入、可延后预取、输出退休；外部IO当前无tag能力，需在DMA/适配层关联事务ID与目的buffer代际。队列槽数、每槽数据/metadata和在途beat独立计账；请求被接收不能释放被消费者仍引用的A/B。
4. **消费反馈与低水位。** 以实际缺数/consumer demand及待退休输出驱动优先级；有界公平保留外部填充推进。不能在缺少形状/依赖信息时将所有外部写降为可延后预取。第2项的可并发地址区间和第3项A引用计数要参与准入。
5. **模式切换屏障。** 仅在算子边界切换，旧DMA、S请求和输出ACK全部退休才释放旧epoch；异常/取消需定义drain或整组reset。生产接口没有原模型两通道32描述符/beat能力证明，不直接复制该上限作为硬件事实。
6. **联合验证。** 同一真实payload比较默认/受限/自适应模式；核对权重与A/B读写字节、尾块、通道队列、无覆盖、计算结果及最后写ACK。先取得完整控制+DMA+P的周期数据，再重放相同模型场景；政策解码/切换时延和端口冲突必须实际收费。

本轮先实现并验证第1项的消费者仲裁基础，与第2/3项共同形成可运行P候选。以上真正DMA步骤仍是明确的实施依赖，不宣称既有模型的10.74%调度收益已经由本仲裁器兑现；完整LLM数值、DDR系统集成、时序/物理/功耗均不在当前孤立bench的验收范围。
